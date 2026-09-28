"""The prep sheet: how much of each liquid must be on the deck at the start, and would anything
run dry?

For every well the robot draws from, the volume needed at the start is the deepest the well is
ever drawn below its starting level: everything asked of it, less what the robot had put into
it by then. That is compared with what the protocol declares. The prep sheet is the list a
student sets the bench up from.

The needed volume is what the robot draws and nothing more. A real tube cannot be emptied to
the last drop (dead volume), which is why needing over 90% of what is declared is flagged too.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from provette.model import Trace, WellKey
from provette.state import Run

NO_MARGIN = 0.90
_EPS = 1e-6
_AIR = (
    "air_gap",
    "tip_at_or_above_well_top",
    "no_tip",
)  # aspirates that never meant to draw liquid

Flag = Literal["would_run_dry", "no_margin", "draws_air"]


@dataclass(frozen=True)
class PrepLine:
    well: WellKey
    slot: str
    labware: str  # the label the author gave, else the labware's display name
    liquid: str  # "" if the protocol declares nothing in this well
    declared_ul: float | None
    needed_ul: float
    flag: Flag | None

    @property
    def already_in_plate(self) -> bool:
        """Declared to hold liquid at the start, and the run never draws it below that level: a
        well the protocol only dispenses into. Printed in its own words, so "load at least 0"
        is never read as "load nothing"."""
        return self.declared_ul is not None and self.needed_ul <= _EPS


@dataclass(frozen=True)
class TipNeed:
    slot: str
    rack: str
    tips: int


@dataclass(frozen=True)
class PrepSheet:
    lines: tuple[PrepLine, ...]  # every well that starts with liquid, or is asked for some
    tips: tuple[TipNeed, ...]

    @property
    def flagged(self) -> tuple[PrepLine, ...]:
        return tuple(line for line in self.lines if line.flag is not None)


def needed_volumes(trace: Trace, run: Run) -> dict[WellKey, float]:
    """For every well drawn from: the least it must hold at the start for the run to work.

    The deepest the replay draws the well below its starting level, plus every microlitre the
    robot asked for and got air instead because the well was short (the replay never invents
    liquid, so a short well gives air, and the shortfall is what was missing).
    """
    short: dict[WellKey, float] = {}
    drawn: set[WellKey] = set()
    for event, step in zip(trace.events, run.steps, strict=True):
        if event.op != "aspirate":
            continue
        for contact in step.contacts:
            if contact.reason in _AIR:
                continue
            drawn.add(contact.well)
            if contact.air_ul > _EPS:
                short[contact.well] = short.get(contact.well, 0.0) + contact.air_ul
    needed = {}
    for well in drawn:
        start = run.initial_wells[well].volume_ul or 0.0
        levels = [
            state.volume_ul for _, state in run.history.get(well, []) if state.volume_ul is not None
        ]
        need = max(0.0, start - min(levels, default=start)) + short.get(well, 0.0)
        if need > _EPS:
            needed[well] = need
    return needed


def prep_sheet(trace: Trace, run: Run) -> PrepSheet:
    labware = {lw.labware_id: lw for lw in trace.deck.labware}
    needed = needed_volumes(trace, run)
    wells = set(needed) | {
        well
        for well, origin in run.origins.items()
        if origin.kind == "declared" and origin.liquid_name
    }
    lines = []
    for well in wells:
        origin = run.origins.get(well)
        declared = origin.initial_volume_ul if origin and origin.kind == "declared" else None
        need = needed.get(well, 0.0)
        flag: Flag | None = None
        if declared is None:
            flag = "draws_air"  # a well the robot filled is asked for more than it was given
        elif need > declared + _EPS:
            flag = "would_run_dry"
        elif need > NO_MARGIN * declared + _EPS:
            flag = "no_margin"
        lw = labware.get(well.labware_id)
        lines.append(
            PrepLine(
                well,
                lw.slot if lw else well.labware_id.split(":")[0],
                (lw.label or lw.display_name) if lw else well.labware_id,
                (origin.liquid_name or "") if origin else "",
                declared,
                need,
                flag,
            )
        )
    lines.sort(
        key=lambda line: (
            int(line.slot) if line.slot.isdigit() else 99,
            int(line.well.well[1:]),
            line.well.well[0],
        )
    )

    used: dict[str, set[str]] = {}
    for event in trace.events:
        if event.op == "pick_up_tip":
            for target in event.targets:
                rack = target.tip or target.well
                used.setdefault(rack.labware_id, set()).add(rack.well)
    tips = tuple(
        TipNeed(
            labware[rack].slot if rack in labware else rack.split(":")[0],
            (labware[rack].label or labware[rack].display_name) if rack in labware else rack,
            len(positions),
        )
        for rack, positions in sorted(used.items())
    )
    return PrepSheet(tuple(lines), tips)
