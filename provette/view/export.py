"""Turn a `CheckResult` (and, with a plate map, a `Verification`) into the one JSON object the
page embeds.

The shape, in words:

* `deck`: the slots in mm, and every labware with its well positions (`geometry.py`) and, per
  well, its outline (shape, diameter or sides, depth, rated maximum), the definition's word for
  its bottom (`bottom`: "flat", "u", "v" or null) and the ledger's own volume-to-height table
  (`height_at_ul`: [µl, mm] rows from [0, 0] to the brim, or null), so the page draws the
  liquid at the height the state computes with (`provette.state.contact.surface_mm`). A
  labware on a module also carries how high the module holds it (`elevation`, mm above the
  deck) and the module's body (`module_body`), from the module's own definition (`_on_module`).
* `wells`: every well the page will ever name, as "labware_id[well]"; everything else refers to
  a well by its index in this list.
* `origins`: every liquid, by the well it started in, with a colour and a plain name.
* `events`: one row per trace event, with a plain-English line.
* `initial`: what the wells hold before event 0.
* `deltas`: one row per event: the wells whose contents changed at that event, with their new
  band list; the tip-rack positions whose status changed; the tips whose residue changed.
  `replay_deltas` applies them and is the Python twin of the page's JavaScript.
* `findings`, `verify`: as `provette check --json` and `provette verify --json` give them.

A band is `[origin, volume_ul, mode, certain]` with mode 0 for bulk and 1 for carry-over,
certain 1 or 0, and volume `null` when it cannot be known.
"""

from __future__ import annotations

import colorsys
import re
from collections.abc import Sequence
from dataclasses import asdict
from functools import cache
from pathlib import Path
from typing import Any

from provette.check import CheckResult
from provette.intent.report import Verification, _well_lines, report_json, report_text
from provette.model import Deck, Event, Labware, Trace, WellKey
from provette.rules import Finding
from provette.rules.common import listing
from provette.state import Run
from provette.state.types import Presence, WellState
from provette.view.geometry import Slot, deck_slots, footprint

# 2: `bottom` and `height_at_ul` on every well row; 3: `mount` on every event; 4: `elevation` and
# `module_body` on every labware row
SCHEMA_VERSION = 4
CACHE_EVERY = 50  # the page keeps a full state every this many events, for fast seeking

# Twelve colours a colour-blind reader can tell apart (Okabe-Ito, then Tableau); past twelve,
# hues spaced by the golden angle.
PALETTE = [
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9",
    "#F0E442", "#7F3C8D", "#11A579", "#E73F74", "#3969AC", "#80BA5A",
]  # fmt: skip


def export(
    result: CheckResult,
    verification: Verification | None = None,
    labware_dirs: Sequence[Path] = (),
) -> dict[str, Any]:
    trace, run = result.trace, result.run
    index = _WellIndex()
    deck = _deck(trace.deck, labware_dirs, trace.deck.api_level)
    origins = _origins(run, trace.deck, index)
    events = [_event(event, trace.deck, index) for event in trace.events]
    initial = {
        str(index.of(well)): _well_row(state, index)
        for well, state in run.initial_wells.items()
        if state.atoms or state.volume_ul
    }
    deltas, held = _deltas(trace, run, index)
    for event, volumes in zip(events, held, strict=True):
        event["held"] = volumes
    findings = [_finding(finding, index) for finding in result.findings]
    verify = _verify(verification, index) if verification is not None else None
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol": result.path.name,
        "api_level": trace.deck.api_level,
        "opentrons_version": trace.deck.opentrons_version,
        "source": list(result.source_lines),
        "deck": deck,
        "pipettes": [
            {"mount": p.mount, "name": p.name, "channels": p.channels} for p in trace.deck.pipettes
        ],
        "wells": index.rows(),
        "origins": origins,
        "events": events,
        "initial": initial,
        "deltas": deltas,
        "cache_every": CACHE_EVERY,
        "findings": findings,
        "summary": _summary(result, verification),
        "verify": verify,
    }


# ---------------------------------------------------------------------------------------------
# Wells and the deck
# ---------------------------------------------------------------------------------------------


class _WellIndex:
    """Every well the page names, numbered in the order first seen."""

    def __init__(self) -> None:
        self._index: dict[WellKey, int] = {}

    def of(self, well: WellKey) -> int:
        if well not in self._index:
            self._index[well] = len(self._index)
        return self._index[well]

    def rows(self) -> list[str]:
        return [str(well) for well in self._index]


def _deck(deck: Deck, labware_dirs: Sequence[Path], api_level: str = "") -> dict[str, Any]:
    slots = deck_slots()
    by_id = {slot.id: slot for slot in slots}
    labware_rows = []
    for labware in deck.labware:
        # Labware off the deck, or in a place the deck definition does not name, is drawn at
        # the origin with the size of slot 1, and the page says so in its label.
        slot = by_id.get(labware.slot, Slot(labware.slot, 0, 0, slots[0].width, slots[0].height))
        labware_rows.append(_labware_row(labware, slot, labware_dirs, api_level))
    return {
        "width": max(s.x + s.width for s in slots),
        "height": max(s.y + s.height for s in slots),
        "slots": [asdict(slot) for slot in slots],
        "labware": labware_rows,
    }


# The OT-2's fixed trash as a protocol below API 2.16 loads it: a labware with one huge "well".
_TRASH_LOAD_NAME = re.compile(r"^opentrons_1_trash_\d+ml_fixed$")


def is_trash(labware: Labware) -> bool:
    """Is this the bin? From API 2.16 the trace records it as a disposal area with no wells
    (`fixedTrash`); before that it is the fixed-trash labware, which the page must not draw as
    a plate with one well (measured: every protocol in the public library does it
    that way)."""
    return (
        labware.load_name == "fixedTrash"
        or not labware.wells
        or bool(_TRASH_LOAD_NAME.match(labware.load_name))
    )


def _labware_row(
    labware: Labware, slot: Slot, labware_dirs: Sequence[Path], api_level: str = ""
) -> dict[str, Any]:
    trash = is_trash(labware)
    if labware.wells and not trash:
        shape = footprint(labware, labware_dirs, slot)
        wells = {
            name: {
                "x": shape.wells[name].x,
                "y": shape.wells[name].y,
                "shape": geometry.shape,
                "d": geometry.diameter_mm,
                "w": geometry.x_mm,
                "h": geometry.y_mm,
                "depth": geometry.depth_mm,
                "max": geometry.max_volume_ul,
                "bottom": geometry.bottom_shape,
                "height_at_ul": (
                    [[volume, height] for volume, height in geometry.height_at_ul]
                    if geometry.height_at_ul
                    else None
                ),
            }
            for name, geometry in labware.wells.items()
        }
        size = {"w": shape.width, "h": shape.height, "ox": shape.offset_x, "oy": shape.offset_y}
        measured = shape.measured
        module = _on_module(labware.module, slot, shape.width, shape.height, api_level)
        if module is not None:
            size["ox"] += module["dx"]
            size["oy"] += module["dy"]
    else:  # the bin: drawn as its slot's box, its one "well" (where tips land) has no place
        wells, measured = {}, True
        size = {"w": slot.width, "h": slot.height, "ox": 0.0, "oy": 0.0}
        module = None
    return {
        "id": labware.labware_id,
        "slot": labware.slot,
        "name": labware.label or labware.display_name,
        "load_name": labware.load_name,
        "is_tiprack": labware.is_tiprack,
        "is_trash": trash,
        "module": labware.module,
        "kind": _kind(labware.labware_id),
        "measured": measured,
        "slot_x": slot.x,
        "slot_y": slot.y,
        **size,
        "elevation": module["elevation"] if module else 0.0,
        "module_body": module["body"] if module else None,
        "wells": wells,
    }


# The thermocycler GEN2's labware offset before API 2.14: the legacy core uses it in place of
# the definition's (opentrons, protocol_api/core/legacy/module_geometry.py, create_geometry).
_LEGACY_TC_BELOW = (2, 14)


@cache
def _module_definition(model: str) -> dict[str, Any] | None:
    from opentrons_shared_data.module import load_definition

    try:
        return dict(load_definition("3", model))
    except Exception:  # a model this opentrons does not know: the labware stays on the deck
        return None


def _on_module(
    model: str | None, slot: Slot, width: float, depth: float, api_level: str
) -> dict[str, Any] | None:
    """Where a module holds its labware and what its body is, from the module's own
    definition (`opentrons_shared_data`): the labware's base is `labwareOffset` from the slot's
    corner, `elevation` mm above the deck (`dx`, `dy` move the labware by the offset's x and y);
    the body is a box under the labware's footprint as tall as the elevation, except the
    thermocycler's, which is the definition's own box (`xDimension` by `yDimension` from its
    `cornerOffsetFromSlot`, covering slots 7, 8, 10 and 11). The OT-2 slot transforms move the
    labware by under a millimetre in the right-hand column and are left out."""
    definition = _module_definition(model) if model else None
    if definition is None or model is None:
        return None
    offset = definition["labwareOffset"]
    if model == "thermocyclerModuleV2" and _version(api_level) < _LEGACY_TC_BELOW:
        from opentrons_shared_data.module import OLD_TC_GEN2_LABWARE_OFFSET

        offset = OLD_TC_GEN2_LABWARE_OFFSET
    elevation = float(offset["z"])
    dx, dy = float(offset["x"]), float(offset["y"])
    if definition.get("moduleType") == "thermocyclerModuleType":
        dims, corner = definition["dimensions"], definition["cornerOffsetFromSlot"]
        body: dict[str, Any] = {
            "x": slot.x + float(corner["x"]),
            "y": slot.y + float(corner["y"]),
            "w": float(dims["xDimension"]),
            "h": float(dims["yDimension"]),
        }
    else:
        body = {"x": slot.x + dx, "y": slot.y + dy, "w": width, "h": depth}
    body["height"] = elevation
    body["name"] = str(definition.get("displayName") or model)
    return {"dx": dx, "dy": dy, "elevation": elevation, "body": body}


def _version(api_level: str) -> tuple[int, int]:
    match = re.match(r"^(\d+)\.(\d+)", api_level or "")
    return (int(match[1]), int(match[2])) if match else (99, 99)


def _kind(labware_id: str) -> str:
    return "tube" if "tube" in labware_id.lower() else "well"


# ---------------------------------------------------------------------------------------------
# Origins and colours
# ---------------------------------------------------------------------------------------------


def colour(n: int) -> str:
    if n < len(PALETTE):
        return PALETTE[n]
    hue = ((n - len(PALETTE)) * 137.508 + 20.0) % 360.0
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.5, 0.75)
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


def _origins(run: Run, deck: Deck, index: _WellIndex) -> list[dict[str, Any]]:
    slots = {lw.labware_id: lw.slot for lw in deck.labware}
    rows = []
    for n, (well, origin) in enumerate(run.origins.items()):
        place = f"{_kind(well.labware_id)} {well.well} in slot {slots.get(well.labware_id, '?')}"
        rows.append(
            {
                "well": index.of(well),
                "name": origin.liquid_name or f"the liquid from {place}",
                "declared": origin.kind == "declared",
                "place": place,
                "volume": origin.initial_volume_ul,
                "colour": colour(n),
            }
        )
    return rows


# ---------------------------------------------------------------------------------------------
# Events, in plain English
# ---------------------------------------------------------------------------------------------


def _event(event: Event, deck: Deck, index: _WellIndex) -> dict[str, Any]:
    targets = [
        [None if t.tip is None else index.of(t.tip), index.of(t.well)] for t in event.targets
    ]
    return {
        "i": event.index,
        "op": event.op,
        "line": event.line,
        "parent": event.parent,
        "t": round(event.t_est_s, 1),
        "vol": event.volume_ul,
        "targets": targets,
        "text": describe(event, deck),
        # the pipette that acts ("left" or "right"); None for a delay or a module step
        "mount": event.mount,
    }


def describe(event: Event, deck: Deck) -> str:
    """One line a student can read: "aspirate 10 µl from tube B1 in slot 2, tip A1"."""
    labware = {lw.labware_id: lw for lw in deck.labware}
    wells = [t.well for t in event.targets]
    tips = [t.tip for t in event.targets if t.tip is not None]
    where = _place(wells, labware)
    with_tip = f", {_tips(tips)}" if tips else ", no tip on the pipette"
    volume = f"{_ul(event.volume_ul)} " if event.volume_ul is not None else ""
    op = event.op
    if op == "pick_up_tip":
        return f"pick up {_tips([t.well for t in event.targets])} from the rack in slot " + (
            labware[wells[0].labware_id].slot if wells and wells[0].labware_id in labware else "?"
        )
    if op == "drop_tip":
        if event.returned:
            return f"put {_tips(tips)} back in the rack"
        return f"drop {_tips(tips)} in the trash"
    if op == "aspirate":
        return f"aspirate {volume}from {where}{with_tip}"
    if op == "dispense":
        return f"dispense {volume}into {where}{with_tip}"
    if op == "blow_out":
        return f"blow out the tip into {where}{with_tip}"
    if op == "touch_tip":
        return f"touch the tip to the wall of {where}{with_tip}"
    if op == "delay":
        return f"wait {_seconds(event.duration_s)}"
    if op == "pause":
        return "pause and wait for the person" + (f": {event.detail}" if event.detail else "")
    if op == "set_temperature":
        degrees = f" to {event.celsius:g} °C" if event.celsius is not None else ""
        return f"set {_module(event.module)}{degrees}"
    if op == "deactivate":
        return f"switch off {_module(event.module)}"
    if op == "thermocycler_profile":
        return "run a thermocycler programme (its steps are not modelled)"
    if op == "lid":
        return f"{event.detail or 'move the lid'}"
    if op == "move_labware":
        return f"move labware: {event.detail or 'to another place'}"
    # a comment of nothing but whitespace (protocols print blank lines) is not a line to show:
    # fall through to the broker's own name for the action ("command.COMMENT" -> "comment")
    detail = (event.detail or "").strip()
    raw = event.raw_op.rpartition(".")[2].replace("_", " ").lower()
    return detail or raw or "another action the simulator reported"


def _place(wells: list[WellKey], labware: dict[str, Labware]) -> str:
    if not wells:
        return "nowhere"
    by_labware: dict[str, list[str]] = {}
    for well in wells:
        by_labware.setdefault(well.labware_id, []).append(well.well)
    parts = []
    for labware_id, names in by_labware.items():
        lw = labware.get(labware_id)
        slot = lw.slot if lw else labware_id.partition(":")[0]
        if lw is not None and is_trash(lw):
            parts.append("the trash")
            continue
        kind = _kind(labware_id) + ("s" if len(names) > 1 else "")
        parts.append(f"{kind} {listing(names, 8)} in slot {slot}")
    return "; ".join(parts)


def _tips(tips: list[WellKey]) -> str:
    names = list(dict.fromkeys(t.well for t in tips))
    if len(names) == 1:
        return f"tip {names[0]}"
    return f"{len(names)} tips ({names[0]} to {names[-1]})"


def _module(model: str | None) -> str:
    text = (model or "module").lower()
    for word, name in (
        ("thermocycler", "the thermocycler"),
        ("temperature", "the temperature module"),
        ("heatershaker", "the heater-shaker"),
        ("magnetic", "the magnetic module"),
    ):
        if word in text:
            return name
    return "the module"


def _ul(volume: float | None) -> str:
    if volume is None:
        return "an unknown amount"
    return f"{volume:g} µl"


def _seconds(seconds: float | None) -> str:
    if seconds is None:
        return "a while"
    if seconds >= 60:
        minutes = seconds / 60
        return f"{minutes:g} minute{'s' if minutes != 1 else ''}"
    return f"{seconds:g} second{'s' if seconds != 1 else ''}"


# ---------------------------------------------------------------------------------------------
# States and deltas
# ---------------------------------------------------------------------------------------------

Band = list[Any]  # [origin, volume, mode, certain]


def _band(origin: int, presence: Presence) -> Band:
    return [
        origin,
        _round(presence.volume_ul),
        0 if presence.mode == "bulk" else 1,
        1 if presence.certain else 0,
    ]


def _well_row(state: WellState, index: _WellIndex) -> list[Any]:
    """[volume_ul or null, min_volume_ul, bands]; bands in the order the well's log has them."""
    bands = [_band(index.of(atom), presence) for atom, presence in state.atoms.items()]
    return [_round(state.volume_ul), _round(state.min_volume_ul), bands]


def _round(volume: float | None) -> float | None:
    """Volumes to the nanolitre: a third of a microlitre is 0.333, not 0.3333333333333333."""
    return None if volume is None else round(volume, 3)


def _deltas(
    trace: Trace, run: Run, index: _WellIndex
) -> tuple[list[dict[str, Any]], list[list[float]]]:
    """One delta per event, and for every event the volume each of its tips holds after it."""
    rows: list[dict[str, Any]] = [{} for _ in trace.events]
    for well, changes in run.history.items():
        for event_index, state in changes:
            if 0 <= event_index < len(rows):
                rows[event_index].setdefault("wells", {})[str(index.of(well))] = _well_row(
                    state, index
                )
    held = _rack_and_tip_deltas(trace, run, index, rows)
    return rows, held


def _rack_and_tip_deltas(
    trace: Trace, run: Run, index: _WellIndex, rows: list[dict[str, Any]]
) -> list[list[float]]:
    """What the page needs about tips, derived from the run's contacts.

    A tip's residue is everything in every well it touched (verdict "contact", or "unknown" for
    an uncertain touch) since it was picked up new; a tip put back in its rack keeps its residue
    and a tip dropped in the trash is gone. This is the state's own rule (README, "Residue"),
    re-read from the contacts rather than re-run, and a test holds the two to each other.

    Fills the "racks" and "tips" parts of the deltas; returns, per event, the volume held by
    each of its tips after the event (in target order), which goes on the event row because it
    changes at nearly every step.
    """
    status: dict[WellKey, str] = {}
    residue: dict[WellKey, dict[int, bool]] = {}
    held: dict[WellKey, float] = {}
    shown: dict[WellKey, list[Any]] = {}
    held_after: list[list[float]] = []
    for event, step in zip(trace.events, run.steps, strict=True):
        row = rows[event.index]
        if event.op == "pick_up_tip":
            for target in event.targets:
                tip = target.well
                if status.get(tip) != "parked":
                    residue[tip] = {}
                    held[tip] = 0.0
                status[tip] = "in_use"
                row.setdefault("racks", []).append([index.of(tip), "in_use"])
        elif event.op == "drop_tip":
            for dropped in (t.tip for t in event.targets if t.tip is not None):
                status[dropped] = "parked" if event.returned else "gone"
                held[dropped] = 0.0
                row.setdefault("racks", []).append([index.of(dropped), status[dropped]])
        for contact in step.contacts:
            if contact.tip is None:
                continue
            bag = residue.setdefault(contact.tip, {})
            if contact.verdict != "no_contact":
                after = run.well_before(contact.well, event.index + 1)
                sure = contact.verdict == "contact"
                for atom, presence in after.atoms.items():
                    number = index.of(atom)
                    bag[number] = bag.get(number, False) or (sure and presence.certain)
            if event.op == "aspirate":
                held[contact.tip] = held.get(contact.tip, 0.0) + contact.liquid_ul
            elif event.op in ("dispense", "blow_out"):
                held[contact.tip] = max(0.0, held.get(contact.tip, 0.0) - contact.liquid_ul)
        for used in (t.tip for t in event.targets if t.tip is not None):
            now = [[atom, 1 if sure else 0] for atom, sure in residue.get(used, {}).items()]
            if shown.get(used) != now:
                shown[used] = now
                row.setdefault("tips", {})[str(index.of(used))] = now
        held_after.append(
            [round(held.get(t.tip, 0.0), 3) if t.tip is not None else 0.0 for t in event.targets]
        )
    return held_after


def replay_deltas(data: dict[str, Any], upto: int | None = None) -> dict[str, Any]:
    """Apply the first `upto` deltas (all of them by default) to the initial state.

    Returns {"wells": {index: [volume, min_volume, bands]}, "racks": {index: status},
    "tips": {index: [[origin, certain], ...]}}. This is exactly what the page's JavaScript does;
    the test compares its final answer with `run.wells`.
    """
    wells: dict[str, list[Any]] = {k: list(v) for k, v in data["initial"].items()}
    racks: dict[str, str] = {}
    tips: dict[str, list[Any]] = {}
    count = len(data["deltas"]) if upto is None else upto
    for delta in data["deltas"][:count]:
        for well, row in delta.get("wells", {}).items():
            wells[well] = row
        for tip, state in delta.get("racks", []):
            racks[str(tip)] = state
        for tip, row in delta.get("tips", {}).items():
            tips[tip] = row
    return {"wells": wells, "racks": racks, "tips": tips}


# ---------------------------------------------------------------------------------------------
# Findings, verification, the summary
# ---------------------------------------------------------------------------------------------


def _finding(finding: Finding, index: _WellIndex) -> dict[str, Any]:
    row = finding.to_json()
    row["root_event"] = finding.occurrences[0].event_index if finding.occurrences else None
    row["well_index"] = [index.of(WellKey(w.labware_id, w.well)) for w in finding.wells]
    row["downstream_index"] = [
        index.of(WellKey(w.labware_id, w.well)) for w in finding.downstream.wells
    ]
    return row


def _verify(v: Verification, index: _WellIndex) -> dict[str, Any]:
    row = report_json(v)
    destination = v.intent.destination
    for result, mismatch in zip(v.intent.mismatches, row["intent"]["mismatches"], strict=True):
        mismatch["text"] = [line.strip() for line in _well_lines(result)]
        mismatch["well_index"] = (
            index.of(WellKey(destination, result.well))
            if destination is not None and result.well is not None
            else None
        )
    text = report_text(v)
    row["destination_name"] = v.intent.destination_name
    row["flags"] = [
        line.strip() for line in text.splitlines() if line.startswith(("  FLAG:", "  Tips:"))
    ]
    row["text"] = text
    return row


def _summary(result: CheckResult, v: Verification | None) -> dict[str, Any]:
    findings = result.findings
    tally = {s: sum(f.severity == s for f in findings) for s in ("error", "warning", "note")}
    if findings:
        parts = [f"{n} {s}{'s' if n > 1 else ''}" for s, n in tally.items() if n]
        n = len(findings)
        check_line = (
            f"Provette found {n} biology problem{'s' if n > 1 else ''} ({', '.join(parts)})."
        )
    else:
        check_line = "Provette found no biology problems."
    verify_line = None
    if v is not None:
        intent = v.intent
        if intent.status == "cannot_check":
            verify_line = f"CANNOT CHECK against plate map {v.platemap.id}: " + "; ".join(
                intent.problems
            )
        else:
            ok = sum(r.ok for r in intent.wells)
            word = "VERIFIED" if intent.status == "verified" else "MISMATCH"
            verify_line = (
                f"{word}: {ok} of {len(intent.wells)} wells hold what plate map "
                f"{v.platemap.id} says."
            )
            if intent.status != "verified":
                bad = len(intent.wells) - ok
                verify_line += f" {bad} well{'s do' if bad != 1 else ' does'} not."
    return {
        "simulator": (
            f"The Opentrons simulator ({result.trace.deck.opentrons_version}) passed this protocol."
        ),
        "check": check_line,
        "verify": verify_line,
        "counts": tally,
        "events": len(result.trace.events),
    }
