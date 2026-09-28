"""Replay a trace into a `Run`: where every liquid went, event by event.

`replay` is the only entry point. It is deterministic, does no I/O and imports nothing from
Opentrons. It never raises on an odd protocol: oddities become `Anomaly` records.
"""

from __future__ import annotations

import gc
from collections.abc import Iterable, Sequence, Set
from dataclasses import replace

from provette.model import Event, LiquidLoad, Trace, WellGeometry, WellKey
from provette.state.contact import EMPTY_UL, aspirate_contact, dispense_contact, surface_mm
from provette.state.run import Run
from provette.state.types import (
    Anomaly,
    AnomalyKind,
    Arrival,
    Contact,
    Mode,
    Origin,
    Presence,
    Reason,
    Step,
    Verdict,
    WellState,
)
from provette.state.working import Amounts, Names, Tip, TipLayer, Well, versions


def replay(trace: Trace, implicit_origins: Iterable[WellKey] = ()) -> Run:
    """Replay every event of `trace`.

    The trace is replayed twice. The first pass only finds the implicit origins: every well with
    no declared liquid that at some point is asked for more than the robot has put into it (so it
    was holding something), and how far below its starting level each is drawn. In a protocol
    that declares liquids, only a well the robot has put nothing into yet can be found this way.
    The second pass is the result: it starts each of those wells, from event 0, as an origin of
    unknown volume with that depth as its lower bound. Both passes move the same volumes (see
    README, "Unknown volumes, and hindsight"), so the second pass finds nothing new.

    This is hindsight: what a step says about a well can depend on a later event proving the well
    held something. `implicit_origins` names wells to treat as implicit origins whatever the trace
    shows; given the implicit origins of a whole run, the steps of a prefix of its trace are a
    prefix of its steps.
    """
    # A crowded deck makes millions of small values, none of them in a cycle. Python's cycle
    # collector would re-walk them all again and again: a third of the time, measured.
    collecting = gc.isenabled()
    gc.disable()
    try:
        first = _Replay(trace, dict.fromkeys(implicit_origins, 0.0), discover=True)
        first.run()
        second = _Replay(trace, first.floors(), discover=False)
        second.run()
        return second.result()
    finally:
        if collecting:
            gc.enable()


def _add(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a + b


def _scale(a: float | None, factor: float) -> float | None:
    return None if a is None else a * factor


# In the first pass a liquid layer in a tip has no atoms that matter, only a volume.
_SOME_LIQUID: Amounts = {-1: 0.0}


# ---------------------------------------------------------------------------------------------
# The replay
# ---------------------------------------------------------------------------------------------


class _Replay:
    def __init__(self, trace: Trace, floors: dict[WellKey, float], discover: bool) -> None:
        self.trace = trace
        self.discover = discover  # the first pass: wells found to be origins change on the spot
        self.declared = {load.well for load in trace.deck.liquid_loads}
        # A protocol that declares liquids has said what is on the deck. Its other wells are empty,
        # except one drawn from before the robot put anything in it (README, "Two regimes").
        self.declares = bool(trace.deck.liquid_loads)
        self.geometry: dict[WellKey, WellGeometry] = {}
        self.wells: dict[WellKey, Well] = {}
        self.tips: dict[WellKey, Tip] = {}
        self.origins: dict[WellKey, Origin] = {}
        self.history: dict[WellKey, list[tuple[int, WellState]]] = {}
        self.initial: dict[WellKey, WellState] = {}
        self.final: dict[WellKey, WellState] = {}
        self.setpoints: dict[str, list[tuple[float, float | None]]] = {}
        self.steps: list[Step] = []
        self.anomalies: list[Anomaly] = []
        self.arrivals: list[Arrival] = []  # of the event being replayed
        self.off_deck: set[WellKey] = set()
        self.overflowed: set[WellKey] = set()
        self.memo: dict[tuple[int, int], bool] = {}
        self.names = Names()
        self.index = 0

        for labware in trace.deck.labware:
            if labware.is_tiprack:
                continue
            for name, geometry in labware.wells.items():
                key = WellKey(labware.labware_id, name)
                self.geometry[key] = geometry
                self.wells[key] = Well(key, self.names, 0.0, 0.0)
        loads: dict[WellKey, list[LiquidLoad]] = {}
        for load in trace.deck.liquid_loads:
            loads.setdefault(load.well, []).append(load)
        for key, well_loads in loads.items():
            volume = sum(load.volume_ul for load in well_loads)
            if volume <= 0:
                continue  # `load_empty`: the well is known to be empty, so it is no origin
            self.origins[key] = Origin(key, "declared", tuple(well_loads), volume, volume, None)
            self.wells[key] = Well(key, self.names, volume, volume)
            self.wells[key].put(self.names.number(key), Presence(volume, "bulk", True, None))
        for key, floor in floors.items():  # implicit origin -> the least it held at the start
            self.origins[key] = Origin(key, "implicit", (), None, floor, None)
            self.wells[key] = Well(key, self.names, None, floor)
            self.wells[key].put(self.names.number(key), Presence(None, "bulk", True, None))
        for key, well in self.wells.items():
            well.dirty = False
            self.initial[key] = well.frozen()
        self.final = dict(self.initial)

    def run(self) -> None:
        for event in self.trace.events:
            self.index = event.index
            self.arrivals = []
            start = {
                t.well: self.wells[t.well].volume for t in event.targets if t.well in self.wells
            }
            contacts = self._apply(event, start)
            for target in event.targets:
                well = self.wells.get(target.well)
                if well is not None and well.dirty:
                    well.dirty = False
                    well.lowest = min(well.lowest, well.min_volume)
                    if not self.discover:  # the first pass is only read for `lowest`
                        state = well.frozen()
                        self.history.setdefault(well.key, []).append((event.index, state))
                        self.final[well.key] = state
            self.steps.append(
                Step(event.index, event.op, event.t_est_s, tuple(contacts), tuple(self.arrivals))
            )

    def floors(self) -> dict[WellKey, float]:
        """implicit origin -> how far below its starting level it was drawn."""
        return {
            key: max(0.0, -self.wells[key].lowest)
            for key, origin in self.origins.items()
            if origin.kind == "implicit"
        }

    def result(self) -> Run:
        last = self.trace.events[-1] if self.trace.events else None
        end_s = 0.0 if last is None else last.t_est_s + (last.duration_s or 0.0)
        return Run(
            steps=tuple(self.steps),
            wells=self.final,
            tips={key: tip.frozen(self.names) for key, tip in self.tips.items()},
            origins=dict(self.origins),
            anomalies=tuple(self.anomalies),
            end_s=end_s,
            initial_wells=self.initial,
            history=self.history,
            setpoints=self.setpoints,
        )

    def _within(self, a: Set[int], v_a: int, b: Set[int], v_b: int) -> bool:
        """Is set `a` inside set `b`? Asked once per pair of versions, then remembered."""
        known = self.memo.get((v_a, v_b))
        if known is None:
            known = self.memo[(v_a, v_b)] = a <= b
        return known

    # -- dispatch -----------------------------------------------------------------------------

    def _apply(self, event: Event, start: dict[WellKey, float | None]) -> list[Contact]:
        if event.op == "pick_up_tip":
            for target in event.targets:
                self._pick_up(target.tip or target.well)
        elif event.op == "drop_tip":
            for target in event.targets:
                if target.tip is not None:
                    self._drop(target.tip, event.returned)
        elif event.op == "aspirate":
            return [self._aspirate(event, t.tip, t.well, start) for t in event.targets]
        elif event.op in ("dispense", "blow_out"):
            return self._dispense(event, start)
        elif event.op == "touch_tip":
            return [
                Contact(
                    t.tip, t.well, "no_contact", "touches_wall_only", event.height_mm, None, 0, 0
                )
                for t in event.targets
            ]
        elif event.op in ("set_temperature", "deactivate"):
            if event.labware_id is not None:
                celsius = event.celsius if event.op == "set_temperature" else None
                self.setpoints.setdefault(event.labware_id, []).append((event.t_est_s, celsius))
        elif event.op == "thermocycler_profile":
            self._note("profile_not_modelled", None, None)
        return []

    def _note(
        self, kind: AnomalyKind, well: WellKey | None, tip: WellKey | None, ul: float | None = None
    ) -> None:
        self.anomalies.append(Anomaly(self.index, kind, well, tip, ul))

    # -- tips ---------------------------------------------------------------------------------

    def _pick_up(self, key: WellKey) -> None:
        old = self.tips.get(key)
        if old is not None and old.status == "parked":
            old.status = "in_use"  # a parked tip keeps its residue
        elif old is not None and old.status == "in_use":
            self._note("tip_picked_up_twice", None, key)
        else:
            self.tips[key] = Tip(key, self.index)

    def _drop(self, key: WellKey, returned: bool) -> None:
        tip = self._tip(key)
        liquid, _ = tip.held()
        if liquid > EMPTY_UL:
            self._note("tip_dropped_with_liquid", None, key, liquid)
        tip.status = "parked" if returned else "dropped"
        tip.layers = []

    def _tip(self, key: WellKey) -> Tip:
        tip = self.tips.get(key)
        if tip is None or tip.status != "in_use":
            self._note("tip_not_picked_up", None, key)
            if tip is None or tip.status == "dropped":
                tip = self.tips[key] = Tip(key, self.index)
            tip.status = "in_use"
        return tip

    # -- wells --------------------------------------------------------------------------------

    def _well(self, key: WellKey) -> Well:
        if key not in self.geometry and key not in self.off_deck:
            self.off_deck.add(key)
            self._note("well_not_on_deck", key, None)
        well = self.wells.get(key)
        if well is None:
            well = self.wells[key] = Well(key, self.names, 0.0, 0.0)
            self.initial[key] = self.final[key] = well.frozen()
        return well

    def _found_implicit_origin(self, well: Well) -> None:
        """First pass only: from here on the well's volume is unknown, as it will be from event 0
        in the second pass. Only the volumes of this pass are used, and they are already right:
        until now the well gave no more than it got, so nothing was held back."""
        self.origins[well.key] = Origin(well.key, "implicit", (), None, 0.0, None)
        well.volume = None
        well.put(self.names.number(well.key), Presence(None, "bulk", True, None))

    def _exchange(self, well: Well, tip: Tip, verdict: Verdict) -> None:
        """The tip is in the liquid (or may be): residue flows both ways.

        Said atom by atom: the tip gains every atom of the well, certain if the contact and the
        well's atom both are, and its source becomes this well unless that would replace a certain
        source by an uncertain one. The well gains, as carry-over, every atom of the tip as it was
        before. Done set by set, so that a meeting with nothing new costs nothing.
        """
        if self.discover:
            return  # the first pass follows volumes only
        sure = verdict == "contact"
        atoms = well.atoms.keys()
        residue = tip.source.keys()

        # What the well will gain, read off before the tip changes, in the tip's order.
        news: set[int] = set()
        if not self._within(residue, tip.v_all, atoms, well.v_all):
            news = residue - atoms
        if sure and not self._within(tip.sure, tip.v_sure, well.sure, well.v_sure):
            news |= tip.sure - well.sure
        tip_sure = tip.sure if sure else ()
        gains = [(a, a in tip_sure, 0.0) for a in sorted(news, key=tip.place.__getitem__)]

        # The tip.
        if not self._within(atoms, well.v_all, residue, tip.v_all):
            for atom in sorted(atoms - residue, key=well.place.__getitem__):
                tip.place[atom] = len(tip.place)
                tip.source[atom] = well.key
                tip.since[atom] = self.index
            tip.v_all = next(versions)
        if sure:
            tip.source.update(well.sure_sources())
            if not self._within(well.sure, well.v_sure, tip.sure, tip.v_sure):
                tip.sure |= well.sure
                tip.v_sure = next(versions)
            unsure: Iterable[int] = atoms - well.sure if len(well.sure) != len(atoms) else ()
        else:
            unsure = () if self._within(atoms, well.v_all, tip.sure, tip.v_sure) else atoms
        for atom in unsure:
            if atom not in tip.sure:
                tip.source[atom] = well.key

        # The well.
        self._arrive_all(well, tip, "carryover", gains)

    # -- aspirate -----------------------------------------------------------------------------

    def _aspirate(
        self,
        event: Event,
        tip_key: WellKey | None,
        key: WellKey,
        start: dict[WellKey, float | None],
    ) -> Contact:
        well = self._well(key)
        if tip_key is None:
            self._note("no_tip", key, None)
            return Contact(None, key, "no_contact", "no_tip", event.height_mm, None, 0.0, 0.0)
        tip = self._tip(tip_key)
        if event.volume_ul is None:
            self._note("missing_volume", key, tip_key)
        asked = max(event.volume_ul or 0.0, 0.0)
        geometry = self.geometry.get(key)
        started_at = start.get(key, well.volume)

        def judge() -> tuple[Verdict, Reason, bool]:
            return aspirate_contact(
                is_air_gap=event.parent == "air_gap",
                geometry=geometry,
                height_mm=event.height_mm,
                volume_before_ul=None if well.volume is None else started_at,
                wants_liquid=asked > 0,
            )

        verdict, reason, draws = judge()
        short = well.volume is not None and asked > well.volume + EMPTY_UL
        gave_more_than_it_got = (
            self.discover
            and short
            and (draws or reason in ("well_empty", "tip_above_surface"))
            and key not in self.declared
            and not (self.declares and well.received)
        )
        if gave_more_than_it_got:
            # Asked for more than the robot ever put in: the well was holding something.
            self._found_implicit_origin(well)
            verdict, reason, draws = judge()
        elif reason == "well_empty" and asked > 0:
            self._note("aspirate_from_empty_well", key, tip_key, asked)
        if reason == "tip_above_column_height" or (reason == "tip_above_surface" and asked > 0):
            self._note("aspirate_above_liquid", key, tip_key, asked)

        if verdict != "no_contact":
            self._exchange(well, tip, verdict)

        liquid = 0.0
        if draws:
            origin = self.origins.get(key)
            if origin is not None and origin.first_drawn_event is None:
                self.origins[key] = replace(origin, first_drawn_event=self.index)
            sized = set() if self.discover else set(well.sized)
            v_keys = well.v_all
            drawn, liquid = self._draw(well, asked, tip_key)
            self._draw_in(tip, TipLayer(liquid, drawn, sized, v_keys, well.place))
        self._draw_in(tip, TipLayer(asked - liquid, None, set(), 0, None))

        surface = surface_mm(geometry, None if well.volume is None else started_at)
        return Contact(
            tip_key, key, verdict, reason, event.height_mm, surface, liquid, asked - liquid
        )

    def _draw(self, well: Well, asked: float, tip: WellKey) -> tuple[Amounts, float]:
        """Take `asked` uL of ideally mixed liquid out of `well`: what was drawn, atom by atom.

        An atom with volume 0.0 (a trace) is drawn as 0.0 and stays 0.0, so only the atoms with a
        volume are worked on.
        """
        drawn = _SOME_LIQUID if self.discover else well.zeros()
        sized = () if self.discover else list(well.sized)
        well.dirty = True
        if well.volume is None:
            # Shares are unknown, unless one atom is all the bulk there is.
            alone = sum(well.atoms[atom].mode == "bulk" for atom in sized) == 1
            for atom in sized:
                drawn[atom] = asked if alone else None
                if not alone:
                    well.put(atom, replace(well.atoms[atom], volume_ul=None))
            well.min_volume -= asked
            return drawn, asked
        liquid = min(asked, well.volume)
        if asked > well.volume + EMPTY_UL:
            self._note("aspirate_exceeds_volume", well.key, tip, asked - well.volume)
        share = liquid / well.volume if well.volume > EMPTY_UL else 0.0
        for atom in sized:
            presence = well.atoms[atom]
            amount = presence.volume_ul
            drawn[atom] = _scale(amount, share)
            rest = None if amount is None else amount - amount * share
            well.put(atom, replace(presence, volume_ul=rest))
        well.volume = well.min_volume = well.volume - liquid
        return drawn, liquid

    def _draw_in(self, tip: Tip, new: TipLayer) -> None:
        """Add a layer at the tip's opening. Liquid drawn onto liquid mixes with it into one."""
        if new.volume <= EMPTY_UL and not new.atoms:
            return
        last = tip.layers[-1] if tip.layers else None
        if last is None or (new.atoms is None) != (last.atoms is None):
            tip.layers.append(new)
            return
        last.volume += new.volume
        if new.atoms is None or last.atoms is None or self.discover:
            return
        fresh: set[int] = set()
        if not self._within(new.atoms.keys(), new.v_keys, last.atoms.keys(), last.v_keys):
            fresh = new.atoms.keys() - last.atoms.keys()
            for atom, amount in new.atoms.items():
                if atom in fresh:
                    last.atoms[atom] = amount
            last.v_keys = next(versions)
            last.place = None
        for atom in new.sized - fresh:
            last.atoms[atom] = _add(last.atoms[atom], new.atoms[atom])
        last.sized |= new.sized

    # -- dispense and blow_out ----------------------------------------------------------------

    def _pour(self, tip: Tip, volume_ul: float) -> TipLayer:
        """Push `volume_ul` out of a tip, last layer first: the liquid that left, as one layer.

        The rest of what left was air. Pushing more than the tip holds empties it.
        """
        out = TipLayer(0.0, {}, set(), 0, None)
        assert out.atoms is not None
        left = volume_ul
        while tip.layers and left > EMPTY_UL:
            layer = tip.layers[-1]
            take = min(left, layer.volume)
            share = take / layer.volume if layer.volume > 0 else 1.0
            stays = layer.volume - take > EMPTY_UL
            if layer.atoms is not None:
                out.volume += take
                if not out.atoms and not stays and share == 1.0:
                    out.atoms = layer.atoms  # the whole layer leaves, as it is
                    out.sized = layer.sized
                    for atom in layer.sized:  # a whole-number volume from a hand-built trace
                        out.atoms[atom] = _add(0.0, _scale(layer.atoms[atom], share))
                    out.v_keys, out.place = layer.v_keys, layer.place
                    tip.layers.pop()
                    left -= take
                    continue
                if not out.atoms:
                    out.atoms = dict.fromkeys(layer.atoms, 0.0)
                    out.v_keys, out.place = layer.v_keys, layer.place
                else:
                    fresh = layer.atoms.keys() - out.atoms.keys()
                    if fresh:
                        out.v_keys, out.place = next(versions), None
                        for atom in layer.atoms:
                            if atom in fresh:
                                out.atoms[atom] = 0.0
                for atom in layer.sized:
                    out.atoms[atom] = _add(out.atoms[atom], _scale(layer.atoms[atom], share))
                out.sized |= layer.sized
                if stays:
                    for atom in layer.sized:
                        amount = layer.atoms[atom]
                        layer.atoms[atom] = None if amount is None else amount - amount * share
            if stays:
                layer.volume -= take
            else:
                tip.layers.pop()
            left -= take
        return out

    def _dispense(self, event: Event, start: dict[WellKey, float | None]) -> list[Contact]:
        # First what leaves each tip, so that every channel is judged against the surface as it
        # stands once all channels have dispensed.
        poured: list[tuple[Tip, TipLayer, float] | None] = []
        incoming: dict[WellKey, float] = {}
        for target in event.targets:
            self._well(target.well)
            if target.tip is None:
                self._note("no_tip", target.well, None)
                poured.append(None)
                continue
            tip = self._tip(target.tip)
            held = sum(tip.held())
            if event.op == "blow_out":
                asked = held
            elif event.volume_ul is None:
                self._note("missing_volume", target.well, target.tip)
                asked = held
            else:
                asked = max(event.volume_ul, 0.0)
            if asked > held + 1e-6:
                self._note("dispense_exceeds_held", target.well, target.tip, asked - held)
            out = self._pour(tip, asked)
            poured.append((tip, out, min(asked, held) - out.volume))
            incoming[target.well] = incoming.get(target.well, 0.0) + out.volume

        contacts = []
        for target, pour in zip(event.targets, poured, strict=True):
            key = target.well
            if pour is None:
                contacts.append(
                    Contact(None, key, "no_contact", "no_tip", event.height_mm, None, 0.0, 0.0)
                )
                continue
            tip, out, air = pour
            liquid = out.volume
            well = self.wells[key]
            geometry = self.geometry.get(key)
            started_at = start.get(key, well.volume)
            after = None if well.volume is None else _add(started_at, incoming[key])
            verdict, reason = dispense_contact(
                geometry=geometry, height_mm=event.height_mm, volume_after_ul=after
            )
            if liquid > EMPTY_UL or out.atoms:
                self._receive(well, tip, out)
                if liquid != 0:
                    well.dirty = True
                well.volume = _add(well.volume, liquid)
                well.min_volume += liquid
                well.received = well.received or liquid > EMPTY_UL
                # What is surely in the well: for an implicit origin only what the robot has net
                # put in, because its floor rests on aspirates that may have drawn air.
                origin = self.origins.get(key)
                floor = origin.min_initial_volume_ul if origin and well.volume is None else 0.0
                surely = well.min_volume - floor
                limit = geometry.max_volume_ul if geometry is not None else None
                if limit is not None and surely > limit + 1e-6 and key not in self.overflowed:
                    self.overflowed.add(key)  # noted once, when it first happens
                    self._note("overflow", key, tip.key, surely - limit)
            if verdict != "no_contact":
                self._exchange(well, tip, verdict)
            contacts.append(
                Contact(
                    tip.key,
                    key,
                    verdict,
                    reason,
                    event.height_mm,
                    surface_mm(geometry, after),
                    liquid,
                    air,
                )
            )
        return contacts

    def _receive(self, well: Well, tip: Tip, out: TipLayer) -> None:
        """The dispensed liquid's atoms arrive in bulk, in their order. A trace the well already
        holds in bulk, as certainly as the tip does, changes nothing, and is skipped."""
        atoms = out.atoms
        if self.discover or atoms is None:
            return  # the first pass follows volumes only
        if self._within(atoms.keys(), out.v_keys, well.bulk_sure, well.v_bulk_sure):
            # No arrival can come of these, so their order does not matter.
            self._arrive_all(well, tip, "bulk", [(a, a in tip.sure, atoms[a]) for a in out.sized])
            return
        news = (atoms.keys() - well.bulk) | ((atoms.keys() & tip.sure) - well.sure) | out.sized
        place = out.place
        ordered = sorted(news, key=place.__getitem__) if place else [a for a in atoms if a in news]
        self._arrive_all(well, tip, "bulk", [(a, a in tip.sure, atoms[a]) for a in ordered])

    def _arrive_all(
        self, well: Well, tip: Tip, mode: Mode, coming: Sequence[tuple[int, bool, float | None]]
    ) -> None:
        """Put each of `coming` (atom, certain, volume) into `well`, in that order, and log an
        arrival for each that is news: an atom new to the well, carry-over becoming bulk, or
        uncertain becoming certain.

        On a crowded deck nearly all of them are traces the well does not hold yet. One
        `Presence` serves all of those, being a value.
        """
        held, keys, source, index = well.atoms, self.names.keys, tip.source, self.index
        trace = {c: Presence(0.0, mode, c, index) for c in (False, True)}
        for atom, certain, volume_ul in coming:
            old = held.get(atom)
            if old is None:
                if volume_ul == 0:
                    well.put_new(atom, trace[certain])
                else:
                    well.put_new(atom, Presence(volume_ul, mode, certain, index))
            else:
                bulk = mode == "bulk" or old.mode == "bulk"
                now_certain = old.certain or certain
                total = old.volume_ul if volume_ul == 0 else _add(old.volume_ul, volume_ul)
                better = (bulk and old.mode != "bulk") or (now_certain and not old.certain)
                if better or total != old.volume_ul:
                    new_mode: Mode = "bulk" if bulk else "carryover"
                    well.put(atom, Presence(total, new_mode, now_certain, old.since_event))
                if not better:
                    continue
            self.arrivals.append(
                Arrival(
                    keys[atom], well.key, mode, certain, volume_ul, tip.key, source[atom], index
                )
            )
        well.renumber()
