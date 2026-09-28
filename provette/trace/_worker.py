"""The subprocess that runs one protocol under the simulator and writes its trace.

Run as `python -m provette.trace._worker <protocol.py> <out.jsonl> [--labware-dir D ...]`.
`provette.trace.trace_protocol` is the only caller. It lives in its own process because the tap
below replaces methods on process-wide Opentrons classes, and because a protocol is somebody
else's code.

How it works: every high-level call in the Opentrons Python API announces itself twice on a
"broker", once before it runs and once after. `_Tap.on_message` stands in front of
`LegacyBroker.publish`, reads the "before" announcements, and turns each into a
`provette.model.Event`. See README.md in this directory for the tables.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any, Literal, cast

from provette.model import (
    Deck,
    Event,
    Labware,
    LiquidLoad,
    Op,
    Pipette,
    Target,
    Trace,
    WellKey,
)
from provette.trace._channels import channel_wells, full_offsets
from provette.trace._geometry import well_geometry
from provette.trace._run import ERROR_MARKER

# Broker name (without the "command." prefix) -> our op. Anything absent becomes "other".
OP_BY_BROKER_NAME: dict[str, Op] = {
    "PICK_UP_TIP": "pick_up_tip",
    "DROP_TIP": "drop_tip",
    "DROP_TIP_IN_DISPOSAL_LOCATION": "drop_tip",
    "ASPIRATE": "aspirate",
    "DISPENSE": "dispense",
    "DISPENSE_IN_DISPOSAL_LOCATION": "dispense",
    "BLOW_OUT": "blow_out",
    "BLOW_OUT_IN_DISPOSAL_LOCATION": "blow_out",
    "TOUCH_TIP": "touch_tip",
    "DELAY": "delay",
    "PAUSE": "pause",
    "TEMPDECK_SET_TEMP": "set_temperature",
    "THERMOCYCLER_SET_BLOCK_TEMP": "set_temperature",
    "THERMOCYCLER_START_SET_BLOCK_TEMP": "set_temperature",
    "HEATER_SHAKER_SET_TARGET_TEMPERATURE": "set_temperature",
    "TEMPDECK_DEACTIVATE": "deactivate",
    "THERMOCYCLER_DEACTIVATE": "deactivate",
    "THERMOCYCLER_DEACTIVATE_BLOCK": "deactivate",
    "HEATER_SHAKER_DEACTIVATE_HEATER": "deactivate",
    "THERMOCYCLER_EXECUTE_PROFILE": "thermocycler_profile",
    "THERMOCYCLER_START_EXECUTE_PROFILE": "thermocycler_profile",
    "THERMOCYCLER_OPEN": "lid",
    "THERMOCYCLER_CLOSE": "lid",
    "HEATER_SHAKER_OPEN_LABWARE_LATCH": "lid",
    "HEATER_SHAKER_CLOSE_LABWARE_LATCH": "lid",
    "MOVE_LABWARE": "move_labware",
}

LID_DIRECTION = {
    "THERMOCYCLER_OPEN": "open",
    "THERMOCYCLER_CLOSE": "close",
    "HEATER_SHAKER_OPEN_LABWARE_LATCH": "open",
    "HEATER_SHAKER_CLOSE_LABWARE_LATCH": "close",
}

# The calls that wrap primitives. An event's `parent` is the innermost of these still running.
PARENTS = {
    "TRANSFER",
    "DISTRIBUTE",
    "CONSOLIDATE",
    "MIX",
    "AIR_GAP",
    "TRANSFER_WITH_LIQUID_CLASS",
    "DISTRIBUTE_WITH_LIQUID_CLASS",
    "CONSOLIDATE_WITH_LIQUID_CLASS",
}

# Ops that put a tip in, over or against a well.
WELL_OPS = {"aspirate", "dispense", "blow_out", "touch_tip"}

Mount = Literal["left", "right"]


@dataclass
class _Open:
    """A broker message that has had its "before" and not yet its "after"."""

    name: str
    air_gap: dict[str, Any] | None = None  # set for AIR_GAP: what to emit if nothing is nested


@dataclass
class _Position:
    """Where a pipette last was: enough to place an action that names no location."""

    labware: Any
    well_name: str
    height_mm: float | None


@dataclass
class _Tap:
    protocol_name: str
    events: list[Event] = field(default_factory=list)
    liquid_loads: list[LiquidLoad] = field(default_factory=list)
    contexts: list[Any] = field(default_factory=list)
    failure: str | None = None  # a bug in this file, as opposed to an error in the protocol

    _open: list[_Open] = field(default_factory=list)
    _labware: dict[Any, tuple[str, Any]] = field(default_factory=dict)
    _tips: dict[str, list[WellKey | None]] = field(default_factory=dict)  # mount -> per channel
    _taken: set[WellKey] = field(default_factory=set)  # rack wells whose tip is gone
    _position: dict[str, _Position] = field(default_factory=dict)  # mount -> last well
    _disposal: dict[str, Labware] = field(default_factory=dict)
    _estimator: Any = None
    _clock_s: float = 0.0  # the estimator's increments, summed as they arrive
    _counted: int = 0
    _opentrons_dir: str = ""

    # -- the broker ---------------------------------------------------------------------------

    def on_message(self, message: Any) -> None:
        try:
            if message["$"] == "before":
                self._before(message, sys._getframe(2))
            else:
                self._after(message)
        except Exception:
            self.failure = traceback.format_exc()
            raise
        # Opentrons' own duration estimate, fed by hand. It only counts "after" messages, and a
        # step it cannot estimate adds nothing to the clock.
        with contextlib.suppress(Exception):
            self._estimator.on_message(message)
        # The estimator's own total re-adds every step each time it is asked, which made a
        # 25,000-step protocol take ten times as long to trace as to simulate. Keep our own sum.
        increments = self._estimator._increments
        for entry in increments[self._counted :]:
            self._clock_s += float(entry.duration)
        self._counted = len(increments)

    def _before(self, message: Any, frame: FrameType) -> None:
        name = str(message["name"]).split(".", 1)[-1]
        payload: dict[str, Any] = message["payload"]
        call_args = _publisher_locals(frame)
        line, stack = self._protocol_frames(frame)
        parent = self._parent()
        opened = _Open(name=name)
        self._open.append(opened)

        from opentrons.protocol_api import InstrumentContext, ModuleContext

        owner = payload.get("instrument") or call_args.get("self")
        instrument = owner if isinstance(owner, InstrumentContext) else None
        module = owner if isinstance(owner, ModuleContext) else None
        mount: Mount | None = (
            cast(Mount, str(instrument.mount).lower()) if instrument is not None else None
        )

        op: Op = OP_BY_BROKER_NAME.get(name, "other")
        volume = payload.get("volume")
        common: dict[str, Any] = {
            "line": line,
            "stack": stack,
            "parent": parent,
            "mount": mount,
            "t_est_s": round(self._clock_s, 2),
            "detail": str(payload.get("text", "")),
            "raw_op": str(message["name"]),
        }

        if name == "AIR_GAP" and instrument is not None and mount is not None:
            # From API 2.22 an air gap is a single step with nothing nested in it; before that
            # it wraps an ordinary ASPIRATE. Remember enough to emit the aspirate ourselves if
            # none arrives (`_after`).
            if volume is None:
                volume = instrument._core.get_available_volume()
            opened.air_gap = {
                **common,
                "parent": "air_gap",
                "volume_ul": float(volume),
                "rise_mm": None if call_args.get("in_place") else (payload.get("height") or 5.0),
                "instrument": instrument,
            }
        if name == "ASPIRATE":
            for outer in reversed(self._open[:-1]):
                if outer.air_gap is not None:
                    outer.air_gap = None  # the old form: the nested aspirate is the air gap
                    break

        if op == "dispense" and volume is not None and instrument is not None:
            # Up to API 2.16, asking for more than the tip holds dispenses what it holds (from
            # 2.17 it is an error). The broker announces what was asked for.
            volume = min(float(volume), float(instrument._core.get_current_volume()))

        targets: list[Target] = []
        height: float | None = None
        returned = False
        if instrument is not None and mount is not None:
            location = payload.get("location")
            if location is None and op == "touch_tip":
                location = call_args.get("location")
            if op == "pick_up_tip":
                targets = self._pick_up(instrument, mount, location)
            elif op == "drop_tip":
                targets, returned = self._drop(instrument, mount, location)
            elif op in WELL_OPS:
                targets, height = self._enter(instrument, mount, location)
                if op == "touch_tip" and targets:
                    position = self._position[mount]
                    depth = _definition(position.labware)["wells"][position.well_name]["depth"]
                    height = round(depth + float(call_args.get("v_offset", -1.0)), 3)
            elif name == "MOVE_TO":
                self._enter(instrument, mount, location)  # only to remember where it went

        labware_id: str | None = None
        module_model: str | None = None
        celsius: float | None = None
        if module is not None:
            module_model = _module_model(module)
            if module.labware is not None:
                labware_id = self._labware_id(module.labware)
            if op == "set_temperature":
                for key in ("celsius", "temperature"):
                    value = payload.get(key, call_args.get(key))
                    if value is not None:
                        celsius = float(value)
        if op == "move_labware":
            labware_id = self._labware_id(call_args["labware"])  # before it moves: D-09 id rule
        if op == "lid":
            common["detail"] = f"{LID_DIRECTION[name]}: {common['detail']}"

        duration: float | None = None
        if op == "delay":
            duration = float(payload.get("minutes") or 0) * 60 + float(payload.get("seconds") or 0)

        self._emit(
            op=op,
            targets=targets,
            volume_ul=float(volume) if volume is not None and op in WELL_OPS else None,
            height_mm=height,
            duration_s=duration,
            celsius=celsius,
            module=module_model,
            labware_id=labware_id,
            returned=returned,
            **common,
        )

    def _after(self, message: Any) -> None:
        opened = self._open.pop()
        gap = opened.air_gap
        if gap is None or message.get("error") is not None:
            return
        instrument = gap.pop("instrument")
        rise = gap.pop("rise_mm")
        mount = gap["mount"]
        position = self._position.get(mount)
        targets: list[Target] = []
        height: float | None = None
        if position is not None:
            targets, _ = self._enter(instrument, mount, None)
            if rise is None:
                height = position.height_mm  # in place: the tip did not move
            else:
                depth = _definition(position.labware)["wells"][position.well_name]["depth"]
                height = round(depth + float(rise), 3)
                position.height_mm = height
        self._emit(
            op="aspirate",
            targets=targets,
            height_mm=height,
            duration_s=None,
            celsius=None,
            module=None,
            labware_id=None,
            returned=False,
            **gap,
        )

    def _emit(self, **fields: Any) -> None:
        self.events.append(Event(index=len(self.events), **fields))

    def _parent(self) -> str | None:
        names = [o.name for o in self._open if o.name in PARENTS]
        if not names:
            return None
        if names[-1] == "TRANSFER" and len(names) > 1 and names[-2] != "TRANSFER":
            # distribute() and consolidate() are built on transfer(); name the call the author made
            return names[-2].lower()
        return names[-1].lower()

    # -- source lines -------------------------------------------------------------------------

    def _protocol_frames(self, frame: FrameType | None) -> tuple[int | None, list[str]]:
        """`line` (the innermost protocol line) and `stack` (protocol frames, outermost first)."""
        found: list[str] = []
        line: int | None = None
        while frame is not None:
            filename = frame.f_code.co_filename
            ours = os.path.basename(filename) == self.protocol_name
            if ours and not filename.startswith(self._opentrons_dir):
                if line is None:
                    line = frame.f_lineno
                found.append(f"{frame.f_code.co_name}:{frame.f_lineno}")
            frame = frame.f_back
        return line, found[::-1]

    # -- labware identity ---------------------------------------------------------------------

    def _labware_id(self, labware: Any) -> str:
        """ "<slot>:<load_name>", fixed the first time the labware is seen, so a later
        `move_labware` does not change it."""
        core = labware._core
        key = getattr(core, "labware_id", None) or id(core)
        if key not in self._labware:
            from opentrons.protocols.api_support.labware_like import LabwareLike

            slot = str(LabwareLike(labware).first_parent())
            labware_id = f"{slot}:{_definition(labware)['parameters']['loadName']}"
            if any(labware_id == known for known, _ in self._labware.values()):
                raise RuntimeError(f"two labware share the id {labware_id!r}")
            self._labware[key] = (labware_id, labware)
        return self._labware[key][0]

    # -- tips and wells -----------------------------------------------------------------------

    def _resolve(self, location: Any) -> tuple[Any, str, float | None] | str | None:
        """A broker location as (labware, well name, height above the well bottom), or the id of
        a disposal area, or None when it is not in a well."""
        from opentrons import types
        from opentrons.protocol_api.labware import Well

        if isinstance(location, Well):
            return location.parent, str(location.well_name), None
        if isinstance(location, types.Location):
            if not location.labware.is_well:
                return None
            well = location.labware.as_well()
            height = round(float(location.point.z - well.bottom().point.z), 3)
            return well.parent, str(well.well_name), height
        area = getattr(location, "area_name", None)
        if area is not None:  # TrashBin, WasteChute
            slot = getattr(getattr(location, "location", None), "value", "")
            disposal_id = f"{slot}:{area}"
            self._disposal.setdefault(
                disposal_id,
                Labware(
                    labware_id=disposal_id,
                    load_name=str(area),
                    display_name=type(location).__name__,
                    slot=str(slot),
                    is_tiprack=False,
                    module=None,
                    label=None,
                    wells={},
                ),
            )
            return disposal_id
        return None

    def _pick_up(self, instrument: Any, mount: str, location: Any) -> list[Target]:
        resolved = self._resolve(location)
        if not isinstance(resolved, tuple):
            return []
        labware, well_name, _ = resolved
        labware_id = self._labware_id(labware)
        names = channel_wells(_definition(labware), well_name, _offsets(instrument))
        under = [None if name is None else WellKey(labware_id, name) for name in names]
        if all(key is None or key in self._taken for key in under):
            # Every tip this pickup reaches for is already gone, and the simulator let it
            # happen. Protocols do this after a pause that says "replace the tip rack": the
            # person refilled it and the API was never told. A pipette that came up with
            # nothing could not do the pipetting that follows, so take the rack as refilled.
            self._taken.difference_update(key for key in under if key is not None)
        # A tip already taken from a rack that is otherwise in use: this channel comes up empty.
        tips = [None if key in self._taken else key for key in under]
        self._taken.update(key for key in tips if key is not None)
        self._tips[mount] = tips
        return [Target(tip=tip, well=tip) for tip in tips if tip is not None]

    def _drop(self, instrument: Any, mount: str, location: Any) -> tuple[list[Target], bool]:
        tips = self._tips.pop(mount, [])
        self._position.pop(mount, None)
        resolved = self._resolve(location)
        if resolved is None:
            return [], False
        if isinstance(resolved, str):
            return [Target(tip, WellKey(resolved, "A1")) for tip in tips if tip is not None], False
        labware, well_name, _ = resolved
        labware_id = self._labware_id(labware)
        definition = _definition(labware)
        if not definition["parameters"]["isTiprack"]:
            key = WellKey(labware_id, well_name)
            return [Target(tip, key) for tip in tips if tip is not None], False
        targets = []
        names = channel_wells(definition, well_name, _offsets(instrument))
        for tip, name in zip(tips, names, strict=False):
            if tip is not None:
                key = WellKey(labware_id, name or well_name)  # as in `_enter`: never lose a tip
                self._taken.discard(key)  # a returned tip can be picked up again
                targets.append(Target(tip, key))
        return targets, True

    def _enter(
        self, instrument: Any, mount: str, location: Any
    ) -> tuple[list[Target], float | None]:
        """The targets of an action in a well. With no location, the pipette's last well."""
        resolved = self._resolve(location)
        tips = self._tips.get(mount)
        if isinstance(resolved, str):
            self._position.pop(mount, None)
            return [Target(tip, WellKey(resolved, "A1")) for tip in tips or [] if tip], None
        if resolved is None:
            position = self._position.get(mount)
            if location is not None:
                self._position.pop(mount, None)  # somewhere that is not a well
                return [], None
            if position is None:
                return [], None
        else:
            position = _Position(*resolved)
            self._position[mount] = position
        labware_id = self._labware_id(position.labware)
        names = channel_wells(
            _definition(position.labware), position.well_name, _offsets(instrument)
        )
        # Every tip on the pipette takes part in every action: one target per tip, always. A
        # channel over no well of the definition (tips between the tubes of a tube rack, a
        # flat "surface" labware drawn as one small well) is booked to the well the protocol
        # named. That is what the simulator does with the liquid, it keeps each tip's volume
        # adding up, and it errs towards reporting contact. See README, "A channel over no well".
        wells = [WellKey(labware_id, name or position.well_name) for name in names]
        if tips is None:
            return [Target(None, well) for well in wells], position.height_mm  # no tip on at all
        targets = [
            Target(tip, well) for tip, well in zip(tips, wells, strict=False) if tip is not None
        ]
        return targets, position.height_mm

    # -- liquids ------------------------------------------------------------------------------

    def rack_refilled(self, labware: Any) -> None:
        """`tiprack.reset()` or `pipette.reset_tipracks()`: a person put a full rack there."""
        labware_id = self._labware_id(labware)
        self._taken = {key for key in self._taken if key.labware_id != labware_id}

    def record_loads(self, labware: Any, volumes: dict[str, float], liquid: Any) -> None:
        line, _ = self._protocol_frames(sys._getframe(2))
        labware_id = self._labware_id(labware)
        for well_name, volume in volumes.items():
            self.liquid_loads.append(
                LiquidLoad(
                    well=WellKey(labware_id, well_name),
                    liquid_name="" if liquid is None else str(liquid.name),
                    description=None if liquid is None else liquid.description,
                    volume_ul=float(volume),
                    line=line,
                )
            )

    # -- the deck header ----------------------------------------------------------------------

    def deck(self) -> Deck:
        import opentrons

        if not self.contexts:
            raise RuntimeError("the simulator never created a ProtocolContext")
        context = self.contexts[-1]
        modules = {str(slot): module for slot, module in context.loaded_modules.items()}
        for labware in context.loaded_labwares.values():
            self._labware_id(labware)
        for module in modules.values():
            if module.labware is not None:
                self._labware_id(module.labware)

        rows = []
        for labware_id, labware in self._labware.values():
            definition = _definition(labware)
            slot = labware_id.split(":", 1)[0]
            label = labware._core.get_user_display_name()
            rows.append(
                Labware(
                    labware_id=labware_id,
                    load_name=definition["parameters"]["loadName"],
                    display_name=definition["metadata"]["displayName"],
                    slot=slot,
                    is_tiprack=bool(definition["parameters"]["isTiprack"]),
                    module=_module_model(modules[slot]) if slot in modules else None,
                    label=None if label is None else str(label),
                    wells={name: well_geometry(definition, name) for name in definition["wells"]},
                )
            )
        rows.extend(self._disposal.values())
        rows.sort(key=lambda row: (int(row.slot) if row.slot.isdigit() else 99, row.labware_id))
        pipettes = [
            Pipette(
                mount=cast(Mount, str(mount).lower()),
                name=str(instrument.name),
                channels=int(instrument.channels),
                min_volume_ul=float(instrument.min_volume),
                max_volume_ul=float(instrument.max_volume),
            )
            for mount, instrument in sorted(context.loaded_instruments.items())
        ]
        return Deck(
            protocol_name=self.protocol_name,
            api_level=str(context.api_version),
            opentrons_version=str(opentrons.__version__),
            labware=rows,
            pipettes=pipettes,
            liquid_loads=self.liquid_loads,
        )


def _publisher_locals(frame: FrameType | None) -> dict[str, Any]:
    """The arguments of the Opentrons API method that published this message.

    Module payloads carry only text, and so does MOVE_LABWARE, so this is the one place the
    module object, a heater-shaker's target temperature or the labware being moved can be read.
    Every message is published from inside `publish_context`, a context manager; the frame
    that entered it is either the `@publish` decorator, which keeps the method's arguments in
    `func_args`, or the method itself (aspirate, dispense, move_labware).
    """
    while frame is not None and frame.f_code.co_name != "__enter__":
        frame = frame.f_back
    caller = frame.f_back if frame is not None else None
    if caller is None:
        return {}
    if caller.f_code.co_name == "_decorated":
        return dict(caller.f_locals.get("func_args", {}))
    return dict(caller.f_locals)


def _definition(labware: Any) -> dict[str, Any]:
    return cast(dict[str, Any], labware._core.get_definition())


def _module_model(module: Any) -> str:
    model = module._core.get_model()
    return str(getattr(model, "value", model))


def _offsets(instrument: Any) -> list[float]:
    """Each active channel's y position relative to the first active one.

    From API 2.18 a pipette can be told to use only some of its nozzles, and the engine keeps a
    map of the active ones; before that every channel is always active.
    """
    try:
        nozzle_map = instrument._core.get_nozzle_map()
    except Exception:  # the old engine raises APIVersionError here
        return full_offsets(int(instrument.channels))
    start = nozzle_map.map_store[nozzle_map.starting_nozzle]
    return [float(point.y - start.y) for point in nozzle_map.map_store.values()]


def _install(tap: _Tap) -> None:
    import opentrons
    from opentrons.legacy_broker import LegacyBroker
    from opentrons.protocol_api import ProtocolContext
    from opentrons.protocol_api.labware import Labware as ApiLabware
    from opentrons.protocol_api.labware import Well
    from opentrons.protocols.duration.estimator import DurationEstimator

    tap._estimator = DurationEstimator()
    tap._opentrons_dir = os.path.dirname(opentrons.__file__)

    original_publish = LegacyBroker.publish

    def publish(self: Any, topic: Any, message: Any) -> None:  # called with `message=` by name
        tap.on_message(message)
        original_publish(self, topic, message)

    LegacyBroker.publish = publish

    original_init = ProtocolContext.__init__

    def init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        tap.contexts.append(self)

    ProtocolContext.__init__ = init

    # Liquids are declared, not moved, so the broker never hears of them: wrap the public calls.
    well_load = Well.load_liquid
    labware_load = ApiLabware.load_liquid
    labware_load_by_well = ApiLabware.load_liquid_by_well
    labware_load_empty = ApiLabware.load_empty

    def names(labware: Any, wells: Any) -> list[str]:
        return [w if isinstance(w, str) else str(w.well_name) for w in wells]

    def load_liquid(self: Any, liquid: Any, volume: float) -> None:
        well_load(self, liquid, volume)
        tap.record_loads(self.parent, {str(self.well_name): volume}, liquid)

    def labware_load_liquid(self: Any, wells: Any, volume: float, liquid: Any) -> None:
        labware_load(self, wells, volume, liquid)
        tap.record_loads(self, dict.fromkeys(names(self, wells), volume), liquid)

    def load_liquid_by_well(self: Any, volumes: Any, liquid: Any) -> None:
        labware_load_by_well(self, volumes, liquid)
        by_name = dict(zip(names(self, volumes), volumes.values(), strict=True))
        tap.record_loads(self, by_name, liquid)

    def load_empty(self: Any, wells: Any) -> None:
        labware_load_empty(self, wells)
        tap.record_loads(self, dict.fromkeys(names(self, wells), 0.0), None)

    labware_reset = ApiLabware.reset

    def reset(self: Any) -> None:
        labware_reset(self)
        tap.rack_refilled(self)

    ApiLabware.reset = reset
    Well.load_liquid = load_liquid
    ApiLabware.load_liquid = labware_load_liquid
    ApiLabware.load_liquid_by_well = load_liquid_by_well
    ApiLabware.load_empty = load_empty


def _error_text(error: BaseException) -> str:
    """The simulator's own sentence. The new engine wraps it in a list of error records."""
    first = error.args[0] if error.args else None
    if isinstance(first, list) and first and hasattr(first[0], "detail"):
        return "; ".join(str(occurrence.detail) for occurrence in first)
    return f"{type(error).__name__}: {error}" if not str(error).strip() else str(error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provette.trace._worker")
    parser.add_argument("protocol", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--labware-dir", action="append", default=[], type=Path)
    args = parser.parse_args(argv)

    logging.disable(logging.WARNING)
    from opentrons import simulate

    tap = _Tap(protocol_name=args.protocol.name)
    _install(tap)
    try:
        with args.protocol.open(encoding="utf-8") as handle:
            simulate.simulate(
                handle,
                file_name=str(args.protocol),
                custom_labware_paths=[str(d) for d in args.labware_dir],
                log_level="none",
            )
        Trace(deck=tap.deck(), events=tap.events).dump(args.out)
    except Exception as error:  # whatever the protocol raised is the report
        text = _error_text(error)
        if tap.failure is not None:
            text = f"bug in the Provette tracer, not in the protocol:\n{tap.failure}"
        found = re.search(r"\[line (\d+)\]", text)
        report = {"error": text, "line": int(found.group(1)) if found else None}
        print(ERROR_MARKER + json.dumps(report), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
