"""WELL-CAPACITY: more liquid is put into a well than the labware says it can hold.

In words. Every labware definition states a maximum for its wells: a NEST 96-well PCR plate
100 ul a well, a flat 200 ul plate 200 ul, a 1.5 ml tube 1,500 ul. That number is the maker's
working volume, not the rim: by the same definition's shape the "100 ul" PCR well holds about
217 ul to the rim, the "200 ul" flat well 368, the 1.5 ml tube 1,898. Past the rim the liquid
runs into the neighbouring wells and onto the deck; between the stated maximum and the rim it
climbs the wall, wets the seal, and spills when a tip mixes it. The plate map still "verifies"
either way, because the volumes add up on paper, and the simulator says nothing. A serial
dilution written for a 200 ul plate but run in a 100 ul PCR plate is the case that motivated
this rule (a Super draft in eval/agent verified 12 of 12 wells that way). Over the public protocol
library, 117 of 123 wells over the stated maximum were under the rim, which is why the rim and
not the stated maximum decides the severity.

Three findings, one root line each:

* past the rim, when the shape is known: an **error**, once per well, at the first event that
  crosses it;
* past the stated maximum but under the rim, or with no rim known (every custom definition):
  a **warning**, once per well, with both numbers in the text;
* a mixing stroke of a tenth of the well or more, in a well nine tenths full (of the rim when
  known, else of the stated maximum): a **warning**, because the stroke's air and the tip's own
  displacement push liquid out;
* a `load_liquid` that declares more than the well holds (the rim when known, else the stated
  maximum): a **note**, because the prep sheet cannot be followed as written. A declaration is
  not a step, so the note is anchored on the first draw from that well.

What it does not fire on: labware whose label or load name says waste or trash; a sink, a well
in a reservoir, tube, beaker, bottle, trough or container that is only ever dispensed into and
never drawn from, whatever it is called (a plate is never a sink: a destination plate is only
ever dispensed into too, and that is the case the rule is for); a well within 1% or 1 ul of the
limit; a definition with no stated maximum; a mixing stroke under a tenth of the well
(MIX-TOO-WEAK's concern, not ours).

What it says but cannot decide: when a `pause` (or a `delay` with a message) comes between the
well's last draw and the dispense that crosses the limit, the finding adds one sentence saying
so. Four library protocols empty a filter or bead plate by hand or on a plate washer at such
a pause; the script cannot show that, so the finding stands at its severity and says where the
pause is.
"""

from __future__ import annotations

import re

from provette.model import Event, Trace, WellGeometry, WellKey
from provette.rules import sources
from provette.rules.common import Facts, facts_of, stack_key, times, well_count, well_listing
from provette.rules.finding import Downstream, Finding, Severity, WellRef
from provette.rules.rule import Rule
from provette.state import Run

RULE_ID = "WELL-CAPACITY"
MIX_SHARE = 0.9  # a mix stroke in a well this full pushes liquid out
STROKE_SHARE = 0.1  # a stroke smaller than this share of the well spills nothing
SLACK_SHARE = 0.01  # within this share of the limit, or within SLACK_UL, nothing is said
SLACK_UL = 1.0
EXEMPT_WORDS = ("waste", "trash")
SINK_WORDS = ("reservoir", "tube", "beaker", "bottle", "trough", "container")  # never a plate
# a `delay` with a message reads "Delaying for 0 minutes and 30.0 seconds. <message>"
DELAY_WITH_MESSAGE = re.compile(r"^Delaying for \d+ minutes and [\d.]+ seconds\. \S")


def is_pause(event: Event) -> bool:
    """A `pause`, or a `delay` that carries a message: a step where a person may act."""
    return event.op == "pause" or (
        event.op == "delay" and DELAY_WITH_MESSAGE.match(event.detail) is not None
    )


class Capacity:
    """What a well can take, from the labware definition; shared with the declared rule shape
    `full_well_not_mixed` (`provette/rules/declared.py`), which asks the same questions."""

    def __init__(self, facts: Facts) -> None:
        self._labware = {lw.labware_id: lw for lw in facts.trace.deck.labware}
        self._drawn_from = {move.well for move in facts.moves if move.is_aspirate}

    def geometry(self, well: WellKey) -> WellGeometry | None:
        lw = self._labware.get(well.labware_id)
        shape = lw.wells.get(well.well) if lw else None
        if shape is None or not shape.max_volume_ul or shape.max_volume_ul <= 0:
            return None  # a custom definition with no maximum says nothing
        return shape

    def exempt(self, well: WellKey) -> bool:
        lw = self._labware.get(well.labware_id)
        text = " ".join(
            filter(None, (well.labware_id, lw.label if lw else "", lw.display_name if lw else ""))
        ).lower()
        if any(word in text for word in EXEMPT_WORDS):
            return True
        # a sink: a reservoir or tube the robot only ever pours into, whatever it is called
        return any(word in text for word in SINK_WORDS) and well not in self._drawn_from

    def stated(self, well: WellKey) -> float | None:
        shape = self.geometry(well)
        return shape.max_volume_ul if shape else None

    def rim(self, well: WellKey) -> float | None:
        shape = self.geometry(well)
        return shape.brim_ul if shape else None

    def holds(self, well: WellKey) -> float | None:
        """The bigger of the two limits, for the tiers that ask what the well really holds."""
        shape = self.geometry(well)
        if shape is None:
            return None
        return max(shape.max_volume_ul, shape.brim_ul or 0.0)

    @staticmethod
    def slack(limit: float) -> float:
        return max(SLACK_UL, SLACK_SHARE * limit)


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    capacity = Capacity(facts)
    exempt, stated, rim, holds, slack = (
        capacity.exempt,
        capacity.stated,
        capacity.rim,
        capacity.holds,
        capacity.slack,
    )

    def pause_before(well: WellKey, crossing: int) -> Event | None:
        """The last pause between the well's last draw and the dispense that crosses the limit."""
        since = max(
            (e.index for e in trace.events[:crossing] if e.op == "aspirate" and _in(e, well)),
            default=-1,
        )
        pauses = [e for e in trace.events[since + 1 : crossing] if is_pause(e)]
        return pauses[-1] if pauses else None

    def pause_words(well: WellKey, crossing: int) -> str:
        pause = pause_before(well, crossing)
        if pause is None:
            return ""
        return (
            f" A pause at line {pause.line} comes before this step; if the plate is emptied by "
            "hand or on a washer there, the script cannot show it."
        )

    findings: list[Finding] = []

    # 1. past the stated maximum. The state notes the crossing once per well; the volume after
    # each later dispense says whether the rim was crossed too.
    over_max: dict[WellKey, int] = {}
    for anomaly in run.anomalies:
        if anomaly.kind != "overflow" or anomaly.well is None or exempt(anomaly.well):
            continue
        if facts.event(anomaly.event_index).op not in ("dispense", "blow_out"):
            continue
        over_max.setdefault(anomaly.well, anomaly.event_index)
    peak: dict[WellKey, float] = {}
    over_rim: dict[WellKey, int] = {}
    for move in facts.moves:
        if move.is_aspirate or move.well not in over_max:
            continue
        after = run.well_before(move.well, move.event_index + 1).volume_ul
        if after is None:
            continue
        peak[move.well] = max(peak.get(move.well, 0.0), after)
        brim = rim(move.well)
        if brim is not None and after > brim + slack(brim) and move.well not in over_rim:
            over_rim[move.well] = move.event_index

    errors: dict[tuple[str, ...], list[tuple[int, WellKey]]] = {}
    warnings: dict[tuple[str, ...], list[tuple[int, WellKey]]] = {}
    for well, index in over_max.items():
        top = stated(well)
        if top is None or peak.get(well, 0.0) <= top + slack(top):
            continue  # within the slack of the stated maximum: nothing to say
        if well in over_rim:
            index = over_rim[well]
            errors.setdefault(stack_key(facts.event(index)), []).append((index, well))
        else:
            warnings.setdefault(stack_key(facts.event(index)), []).append((index, well))

    for group in errors.values():
        first_index, first_well = group[0]
        first = facts.event(first_index)
        wells = facts.refs(w for _, w in group)
        brim = rim(first_well) or 0.0
        most = max(peak[w] for _, w in group)
        findings.append(
            _finding(
                facts,
                "error",
                f"More liquid than the well can hold: {most:g} ul in a {brim:.0f} ul well, "
                f"{well_count(wells)}",
                (
                    f"At line {first.line} the robot filled {well_listing(wells)} past the rim "
                    f"({brim:.0f} ul to the rim by the labware definition's shape; the maker "
                    f"states {stated(first_well):g} ul)"
                    f"{'' if len(group) == 1 else f' (this line did it {times(len(group))})'}, "
                    f"reaching {most:g} ul. The liquid runs into the neighbouring wells and onto "
                    "the deck; the volumes still add up on paper, so the plate map does not see "
                    f"it, and the simulator says nothing.{pause_words(first_well, first_index)}"
                ),
                "Use labware with bigger wells, or scale every volume down so the fullest well "
                "stays under the stated maximum with room to mix.",
                first_index,
                [i for i, _ in group],
                wells,
            )
        )
    for group in warnings.values():
        first_index, first_well = group[0]
        first = facts.event(first_index)
        wells = facts.refs(w for _, w in group)
        top = stated(first_well) or 0.0
        brim = rim(first_well)
        most = max(peak[w] for _, w in group)
        rim_words = (
            f"under the {brim:.0f} ul the well holds to its rim"
            if brim is not None
            else "and this labware definition does not say where the rim is"
        )
        findings.append(
            _finding(
                facts,
                "warning",
                f"More liquid than the well is rated for: {most:g} ul against {top:g} ul, "
                f"{well_count(wells)}",
                (
                    f"At line {first.line} the robot filled {well_listing(wells)} past the "
                    f"{top:g} ul the maker states for it"
                    f"{'' if len(group) == 1 else f' (this line did it {times(len(group))})'}, "
                    f"reaching {most:g} ul, {rim_words}. Above the stated maximum the liquid "
                    "climbs the wall and wets the seal, a tip going in displaces it over the "
                    "edge, and the volumes still add up on paper, so the plate map does not "
                    f"see it and the simulator says nothing.{pause_words(first_well, first_index)}"
                ),
                "Use labware rated for the volume, or scale every volume down so the fullest "
                "well stays under the stated maximum with room to mix.",
                first_index,
                [i for i, _ in group],
                wells,
            )
        )

    # 2. mixed while nearly full
    warned: set[WellKey] = set()
    near: dict[tuple[str, ...], list[tuple[int, WellKey, float, float]]] = {}
    for move in facts.moves:
        if (
            move not in facts.strokes
            or move.is_aspirate
            or exempt(move.well)
            or move.well in warned
        ):
            continue
        cap = holds(move.well)
        if cap is None or move.liquid_ul < STROKE_SHARE * cap:
            continue  # a stroke that small spills nothing (MIX-TOO-WEAK's concern, not ours)
        volume = run.well_before(move.well, move.event_index + 1).volume_ul
        if volume is None or volume < MIX_SHARE * cap or volume > cap + slack(cap):
            continue  # unknown, not that full, or already over (tier 1 has it)
        warned.add(move.well)
        near.setdefault(stack_key(facts.event(move.event_index)), []).append(
            (move.event_index, move.well, volume, cap)
        )
    for mixed in near.values():
        first_index, first_well, volume, cap = mixed[0]
        first = facts.event(first_index)
        wells = facts.refs(w for _, w, _, _ in mixed)
        findings.append(
            _finding(
                facts,
                "warning",
                f"Mixing in a nearly full well: {volume:.0f} of {cap:.0f} ul, {well_count(wells)}",
                (
                    f"At line {first.line} the tip mixes {well_listing(wells)} holding "
                    f"{volume:g} ul of the {cap:g} ul the well can take"
                    f"{'' if len(mixed) == 1 else f' (this line did it {times(len(mixed))})'}. "
                    "A mixing stroke pushes air and the tip's own volume into the well, and a "
                    "well over nine tenths full spills."
                ),
                "Mix with a smaller stroke, or leave more room in the well.",
                first_index,
                [i for i, _, _, _ in mixed],
                wells,
            )
        )

    # 3. declared over what the well holds. A `load_liquid` is a declaration, not a step, so
    # the finding is anchored on the first step that draws from the well; a well the robot
    # never touches is left alone.
    declared: dict[WellKey, tuple[float, int | None]] = {}
    for load in trace.deck.liquid_loads:
        volume, _ = declared.get(load.well, (0.0, None))
        declared[load.well] = (volume + load.volume_ul, load.line)
    first_draw: dict[WellKey, int] = {}
    for move in facts.moves:
        if move.is_aspirate and move.well not in first_draw:
            first_draw[move.well] = move.event_index
    too_much = [
        (well, volume, load_line, first_draw[well])
        for well, (volume, load_line) in declared.items()
        if well in first_draw
        and (cap := holds(well)) is not None
        and volume > cap + slack(cap)
        and not exempt(well)
    ]
    if too_much:
        too_much.sort(key=lambda row: row[3])
        wells = facts.refs(w for w, _, _, _ in too_much)
        well, volume, load_line, root_index = too_much[0]
        cap = holds(well) or 0.0
        findings.append(
            _finding(
                facts,
                "note",
                f"Declared more than the well holds: {volume:g} ul in a {cap:.0f} ul well, "
                f"{well_count(wells)}",
                (
                    f"At line {facts.event(root_index).line} the robot draws from "
                    f"{well_listing(wells[:1])}, which the protocol declares (line {load_line}) "
                    f"to hold {volume:g} ul; the well holds {cap:g} ul"
                    f"{'' if len(wells) == 1 else f', and {len(wells) - 1} more are like it'}. "
                    "The prep sheet cannot be followed as written."
                ),
                "Declare what the well can really hold, or use a bigger container.",
                root_index,
                [i for _, _, _, i in too_much],
                wells,
            )
        )
    return findings


def _in(event: Event, well: WellKey) -> bool:
    return any(target.well == well for target in event.targets)


def _finding(
    facts: Facts,
    severity: Severity,
    title: str,
    explanation: str,
    fix: str,
    root_index: int,
    indices: list[int],
    wells: tuple[WellRef, ...],
) -> Finding:
    event = facts.event(root_index)
    return Finding(
        rule_id=RULE_ID,
        family=RULE.family,
        tier=RULE.tier,
        severity=severity,
        certain=True,
        roles_basis="none",
        title=title,
        explanation=explanation + f" Wells: {well_listing(wells)}.",
        fix=fix,
        line=event.line,
        stack=tuple(event.stack),
        occurrences=facts.occurrences(indices),
        wells=wells,
        downstream=Downstream(0, ()),
        sources=RULE.sources,
    )


RULE = Rule(
    rule_id=RULE_ID,
    family=9,
    tier="structural",
    title="More liquid than the well holds",
    description=(
        "A dispense takes a well past its rim, by the labware definition's shape: error. Past "
        "the maker's stated maximum but under the rim, or where no rim is known: warning. "
        "Mixing in a well 90% full or more: warning. Declaring that a well starts with more "
        "liquid than it holds: note. "
        "Waste and trash labware, and reservoirs, tubes, beakers, bottles, troughs or "
        "containers only ever poured into, are exempt (a plate never is). When a pause comes "
        "between the well's last draw and the crossing, the finding says so."
    ),
    sources=(sources.OPENTRONS_LABWARE_SCHEMA, sources.LABOP_2023),
    check=check,
)
