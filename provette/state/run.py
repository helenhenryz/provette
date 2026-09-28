"""The result of a replay, and the questions a rule may ask of it."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cached_property

from provette.model import WellKey
from provette.state.types import Anomaly, Arrival, Origin, Step, TempInterval, TipState, WellState


@dataclass(frozen=True)
class Run:
    """Everything the replay learned. Read the fields; ask the methods.

    `steps[i]` is what event i did. `wells` and `tips` are the final states; `tips` keeps every
    tip ever used, dropped ones included. `origins` maps atom id to what is known about it.
    """

    steps: tuple[Step, ...]
    wells: Mapping[WellKey, WellState]
    tips: Mapping[WellKey, TipState]
    origins: Mapping[WellKey, Origin]
    anomalies: tuple[Anomaly, ...]
    end_s: float  # the clock after the last event

    # One entry per (event, well it changed). Memory is one small WellState per liquid action
    # per channel: tens of thousands for the longest protocols.
    initial_wells: Mapping[WellKey, WellState] = field(repr=False)
    history: Mapping[WellKey, list[tuple[int, WellState]]] = field(repr=False)
    setpoints: Mapping[str, list[tuple[float, float | None]]] = field(repr=False)

    @cached_property
    def arrivals(self) -> tuple[Arrival, ...]:
        """Every arrival of the run, in event order."""
        return tuple(arrival for step in self.steps for arrival in step.arrivals)

    @cached_property
    def _firsts(self) -> dict[tuple[WellKey, WellKey], Arrival]:
        firsts: dict[tuple[WellKey, WellKey], Arrival] = {}
        for arrival in self.arrivals:
            firsts.setdefault((arrival.atom, arrival.well), arrival)
        return firsts

    # -- wells and arrivals -------------------------------------------------------------------

    def well_before(self, well: WellKey, event_index: int) -> WellState:
        """The well as it was just before event `event_index`. KeyError if never seen."""
        changes = self.history.get(well, [])
        position = bisect_left(changes, event_index, key=lambda change: change[0])
        return changes[position - 1][1] if position else self.initial_wells[well]

    def first_arrival(self, atom: WellKey, well: WellKey) -> Arrival | None:
        """The arrival that first brought `atom` into `well`; None if it never came, or if
        `well` is the atom's own origin."""
        return self._firsts.get((atom, well))

    def downstream(self, atom: WellKey) -> list[Arrival]:
        """Every well the atom's material reached: the first arrival in each, in event order."""
        return [arrival for (a, _), arrival in self._firsts.items() if a == atom]

    # -- time and temperature -----------------------------------------------------------------

    def time_of(self, event_index: int) -> float:
        """The clock just before event `event_index`; `end_s` for one past the last event."""
        return self.steps[event_index].t_s if event_index < len(self.steps) else self.end_s

    def labware_temperature(
        self, labware_id: str, start_s: float, end_s: float
    ) -> list[TempInterval]:
        """The setpoint of the module under `labware_id` from `start_s` to `end_s`, as intervals.

        A setpoint counts from the moment it is set: the time a module takes to get there is not
        modelled. Labware on no module, or whose module was never set, is ambient throughout.
        """
        intervals = []
        at, celsius = start_s, None
        for when, setpoint in self.setpoints.get(labware_id, []):
            if when >= end_s:
                break
            if when > at:
                intervals.append(TempInterval(at, when, celsius))
                at = when
            celsius = setpoint
        if end_s > at:
            intervals.append(TempInterval(at, end_s, celsius))
        return intervals

    def material_temperature(
        self, atom: WellKey, well: WellKey, before_event: int
    ) -> list[TempInterval]:
        """Where the material of `atom` now in `well` has sat, and how warm, up to `before_event`.

        Follows first arrivals backwards: in `well` since it arrived, before that in the well the
        tip took it from, and so on back to the origin at time 0. The seconds spent inside the
        tip are counted as the well it came from. Empty if the atom was not in the well by then.
        """
        intervals: list[TempInterval] = []
        end_s = self.time_of(before_event)
        here, latest = well, before_event - 1  # the arrival must be no later than `latest`
        while here != atom:
            arrival = self.first_arrival(atom, here)
            if arrival is None or arrival.event_index > latest:
                return []
            moved_s = self.time_of(arrival.event_index)
            intervals = self.labware_temperature(here.labware_id, moved_s, end_s) + intervals
            here, latest, end_s = arrival.source_well, arrival.event_index, moved_s
        return self.labware_temperature(atom.labware_id, 0.0, end_s) + intervals


def seconds_at_or_above(
    intervals: Iterable[TempInterval], celsius: float, ambient_celsius: float
) -> float:
    """Total seconds of `intervals` at `celsius` or warmer; the caller says what ambient is."""
    return sum(
        interval.end_s - interval.start_s
        for interval in intervals
        if (ambient_celsius if interval.celsius is None else interval.celsius) >= celsius
    )
