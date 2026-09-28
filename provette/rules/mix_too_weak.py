"""MIX-TOO-WEAK: a mix that cannot mix the well.

In words. A mix is only a mix if the strokes, together, move the well over a few times. Integra's
serial-dilution protocols draw over 80% of the volume five times; Beckman says "a tip volume just
slightly below the total well volume"; a dairy lab found 800 ul "not anywhere close" to mixing
20 ml however many times it cycled; three mixes gave 11.8% CV where twenty gave 1.7%. Two strokes
of 10 ul in a 505 ul deep well mix nothing, and a 20 ul stroke in a 20 ul well draws air from the
bottom and foams the liquid.

One finding per mix line. A mix is a run of strokes: consecutive aspirate-and-back moves by one
tip in one well, with no other move of that tip between them (`mix()`, `mix_after`,
`mix_before`, or by hand). Where the well's volume before the first stroke is known, the rule
fires on three counts, and says which:

* **Mixing work.** Each stroke moves a share of the well (stroke volume / well volume), and the
  strokes add up: 5 strokes of 30 ul in 200 ul move 0.75 of the well in all. The rule fires when
  that total is under 2.0 wells' worth. So 10 strokes of 45% of the well (4.5) are fine, 3 of 80%
  (2.4) are fine, 3 of 35% (1.05) are not, and 5 of 30% (1.5) are not: a small stroke repeated
  many times does mix.
* **Fewer than three strokes**, whatever their size.
* **A stroke of the whole well or more**, which draws air at the bottom.

It does not fire on a well of unknown volume; on a well that holds only one liquid (the pre-wet
of a tip in a reagent trough), unless that well later receives a second liquid and no other mix
follows; on a stock the protocol only draws from (mixing a stock is resuspension, another rule's
concern); or on a prime: a single stroke in a well followed at once by an aspirate from the same
well with the same tip, which wets the tip and does not claim to mix the well. A single stroke
after a dispense (a rinse of the tip) is still judged.

When the well holds more than the pipette can draw, the share is the stroke over the pipette's
maximum, since a P300 cannot draw 80% of 500 ul; the mixing-work and three-stroke tests then
apply to that. But when the pipette's maximum is under a fifth of the well, no stroke it can make
will mix the well however many times it is repeated, and the rule fires whatever the count; the
fix names the smallest OT-2 pipette that can (P20, P300 or P1000).

The 2.0 and 3 are decisions below the vendors' 80% five times (4.0); they were set by reading
twenty findings from a flood over 787 public protocols, where every false alarm was a stroke of
36 to 48% of the well repeated 4 to 10 times, and so that three strokes of 80% (2.4), short of
the vendors' five but a mix all the same, stay silent. We may raise them.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from provette.model import Pipette, Trace, WellKey
from provette.rules import sources
from provette.rules.common import (
    Facts,
    Move,
    facts_of,
    is_real,
    stack_key,
    times,
    well_count,
    well_listing,
)
from provette.rules.finding import Downstream, Finding, WellRef
from provette.rules.rule import Rule
from provette.state import Run, WellState

RULE_ID = "MIX-TOO-WEAK"
TITLE = "A mix that cannot mix the well"

MIN_WORK = 2.0  # strokes x (stroke / well): under this the strokes move too little in all
MIN_STROKES = 3
CAP_SHARE = 0.2  # a pipette whose maximum is under this share of the well cannot mix it
GOOD_SHARE = 0.8  # what the fix suggests: Integra's "over 80%"
GOOD_STROKES = 5
OT2_PIPETTES: tuple[tuple[str, float], ...] = (("P20", 20.0), ("P300", 300.0), ("P1000", 1000.0))

Reason = str
TOO_LITTLE_WORK: Reason = "too little work"
TOO_FEW: Reason = "too few"
WHOLE_WELL: Reason = "whole well"
PIPETTE_TOO_SMALL: Reason = "pipette too small"


@dataclass(frozen=True)
class _Mix:
    """One run of strokes: one tip, one well, nothing else in between."""

    well: WellKey
    tip: WellKey
    first_index: int  # the event of the first stroke's aspirate
    last_index: int  # the event of the last stroke's dispense
    strokes: int
    stroke_ul: float  # the volume the protocol asks each stroke to draw
    well_ul: float  # what the well held before the first stroke
    work: float  # strokes x (stroke / well), or x (stroke / pipette maximum) when capped
    capped_by: Pipette | None  # set when the well holds more than the pipette can draw
    reasons: tuple[Reason, ...]


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    pipettes: dict[str, Pipette] = {p.mount: p for p in trace.deck.pipettes}
    groups: dict[tuple[str, ...], list[_Mix]] = {}
    for mix in _judged(facts, pipettes):
        groups.setdefault(stack_key(facts.event(mix.first_index)), []).append(mix)

    findings = []
    for group in groups.values():
        first = facts.event(group[0].first_index)
        wells = facts.refs(m.well for m in group)
        found = {r for m in group for r in m.reasons}
        reasons = [
            r for r in (PIPETTE_TOO_SMALL, TOO_LITTLE_WORK, TOO_FEW, WHOLE_WELL) if r in found
        ]
        strokes = _range(m.strokes for m in group)
        stroke_ul = _range(m.stroke_ul for m in group)
        well_ul = _range(m.well_ul for m in group)
        capped = next((m.capped_by for m in group if m.capped_by is not None), None)
        count = len(group)
        explanation = (
            f"At line {first.line} the tip mixes {well_listing(wells)} with "
            f"{strokes} stroke{'' if strokes == '1' else 's'} of {stroke_ul} ul in a well holding "
            f"{well_ul} ul{'' if count == 1 else f' (this line did it {times(count)})'}. "
            + (
                f"The well holds more than the {capped.name} can draw, so the stroke is judged "
                f"against the pipette's {capped.max_volume_ul:g} ul. "
                if capped is not None and PIPETTE_TOO_SMALL not in reasons
                else ""
            )
            + " ".join(_why(r, group, capped) for r in reasons)
            + " Integra draws over 80% of the well five times; three mixes gave 11.8% CV where "
            "twenty gave 1.7%. What the well holds is not at the concentration you calculated, "
            "and in a dilution series every later step inherits the error."
        )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity="warning",
                certain=True,
                roles_basis="none",
                title=_title(reasons, wells, strokes, stroke_ul, well_ul, capped),
                explanation=explanation,
                fix=_fix(group[0], capped),
                line=first.line,
                stack=tuple(first.stack),
                occurrences=facts.occurrences(m.first_index for m in group),
                wells=wells,
                downstream=Downstream(0, ()),
                sources=RULE.sources,
            )
        )
    return findings


def _judged(facts: Facts, pipettes: Mapping[str, Pipette]) -> list[_Mix]:
    """Every run of strokes the rule has something to say about."""
    judged = []
    for moves in _runs(facts):
        first, last = moves[0], moves[-1]
        well, tip = first.well, first.tip
        before = facts.run.well_before(well, first.event_index)
        if before.volume_ul is None or before.volume_ul <= 0:
            continue  # unknown, or nothing there to mix
        if _only_drawn_from(facts, well) or _one_liquid_throughout(facts, well, last.event_index):
            continue
        strokes = sum(m.is_aspirate for m in moves)
        if strokes == 1 and _primes(facts, well, tip, last.event_index):
            continue  # the tip is wetted, not the well mixed
        event = facts.event(first.event_index)
        stroke_ul = event.volume_ul if event.volume_ul is not None else first.liquid_ul
        pipette = pipettes.get(event.mount) if event.mount is not None else None
        capped = pipette if pipette and before.volume_ul > pipette.max_volume_ul else None
        against = capped.max_volume_ul if capped is not None else before.volume_ul
        work = strokes * stroke_ul / against
        reasons = []
        if capped is not None and capped.max_volume_ul < CAP_SHARE * before.volume_ul - 1e-9:
            reasons.append(PIPETTE_TOO_SMALL)
        elif work < MIN_WORK - 1e-9:
            reasons.append(TOO_LITTLE_WORK)
        if strokes < MIN_STROKES:
            reasons.append(TOO_FEW)
        if capped is None and stroke_ul >= before.volume_ul - 1e-9:
            reasons.append(WHOLE_WELL)
        if not reasons:
            continue
        judged.append(
            _Mix(
                well,
                tip,
                first.event_index,
                last.event_index,
                strokes,
                stroke_ul,
                before.volume_ul,
                work,
                capped,
                tuple(reasons),
            )
        )
    return judged


def _title(
    reasons: list[Reason],
    wells: tuple[WellRef, ...],
    strokes: str,
    stroke_ul: str,
    well_ul: str,
    capped: Pipette | None,
) -> str:
    """The finding's title carries the numbers, so the line reads on its own in a list
    ("A mix that cannot mix the well" said the verdict and left the reader to open it):
    the strongest reason first, the well or the count of wells, then strokes × stroke in
    what the well held."""
    where = well_listing(wells) if len(wells) == 1 else well_count(wells)
    numbers = f"{strokes} × {stroke_ul} ul in {well_ul} ul"
    if reasons[0] == PIPETTE_TOO_SMALL and capped is not None:
        return (
            f"A pipette too small to mix {where}: {capped.max_volume_ul:g} ul at most "
            f"in {well_ul} ul"
        )
    if reasons[0] == WHOLE_WELL:
        return f"A mix stroke as big as the well, {where}: {stroke_ul} ul in {well_ul} ul"
    if reasons[0] == TOO_FEW:
        return f"Too few strokes to mix {where}: {numbers}"
    return f"Mixing too weak to stir {where}: {numbers}"


def _runs(facts: Facts) -> list[list[Move]]:
    """The stroke moves of every uninterrupted run of strokes: one tip, one well, in order.

    A run ends when the tip moves liquid anywhere else, or when a tip is picked up afresh.
    """
    runs: list[list[Move]] = []
    open_runs: dict[WellKey, list[Move]] = {}  # tip -> the strokes so far
    moves_by_event: dict[int, list[Move]] = {}
    for move in facts.moves:
        moves_by_event.setdefault(move.event_index, []).append(move)
    for step in facts.run.steps:
        if step.op == "pick_up_tip":
            for target in facts.event(step.event_index).targets:
                closed = open_runs.pop(target.tip or target.well, None)
                if closed is not None:
                    runs.append(closed)
        for move in moves_by_event.get(step.event_index, []):
            current = open_runs.get(move.tip)
            if current is not None and (move not in facts.strokes or current[0].well != move.well):
                runs.append(current)
                del open_runs[move.tip]
                current = None
            if move in facts.strokes:
                if current is None:
                    open_runs[move.tip] = [move]
                else:
                    current.append(move)
    runs.extend(open_runs.values())
    return sorted(runs, key=lambda run: run[0].event_index)


def _primes(facts: Facts, well: WellKey, tip: WellKey, last_index: int) -> bool:
    """Is the tip's next move after this stroke an aspirate from the same well? Then the stroke
    was a prime: the tip is wetted with what it is about to draw, and no mix was claimed."""
    following = next((m for m in facts.moves if m.tip == tip and m.event_index > last_index), None)
    return following is not None and following.is_aspirate and following.well == well


def _only_drawn_from(facts: Facts, well: WellKey) -> bool:
    """A stock the protocol only draws from: it held liquid from the start, liquid is taken out
    of it to use elsewhere, and nothing is ever dispensed into it except its own mixing."""
    return facts.is_stock(well) and not any(
        m.well == well and not m.is_aspirate and m not in facts.strokes for m in facts.moves
    )


def _one_liquid_throughout(facts: Facts, well: WellKey, last_index: int) -> bool:
    """Does the well hold one liquid at this mix, and either never get a second one later, or
    get mixed again after it does? Then this mix is a pre-wet, and there is nothing to judge."""
    if _liquids(facts, facts.run.well_before(well, last_index + 1)) > 1:
        return False
    second_came = False
    for move in facts.moves:
        if move.event_index <= last_index or move.well != well:
            continue
        if move in facts.strokes:
            return True  # another mix follows: that one is judged, not this
        if not move.is_aspirate:
            after = facts.run.well_before(well, move.event_index + 1)
            second_came = second_came or _liquids(facts, after) > 1
    return not second_came


def _liquids(facts: Facts, state: WellState) -> int:
    """How many liquids the well holds, counting liquids declared under one name as one."""
    names = {
        facts.liquid_name(atom) or str(atom)
        for atom, presence in state.atoms.items()
        if is_real(presence)
    }
    return len(names)


def _why(reason: Reason, group: list[_Mix], capped: Pipette | None) -> str:
    if reason == PIPETTE_TOO_SMALL:
        assert capped is not None
        return (
            f"The {_label(capped)} can draw at most {capped.max_volume_ul:g} ul, under a fifth "
            "of the well: no stroke it can make will mix this well, however many times."
        )
    if reason == TOO_LITTLE_WORK:
        strokes = _range(m.strokes for m in group)
        stroke_ul = _range(m.stroke_ul for m in group)
        work = _range(round(m.work, 2) for m in group)
        of_what = "the well" if capped is None else f"the pipette's {capped.max_volume_ul:g} ul"
        worth = "wells' worth" if capped is None else "pipette-fulls"
        return (
            f"{strokes} stroke{'' if strokes == '1' else 's'} of {stroke_ul} ul move {work} of "
            f"{of_what} in all; it takes about {MIN_WORK:g} {worth} of strokes to mix (the "
            "mixing work)."
        )
    if reason == TOO_FEW:
        return f"Fewer than {MIN_STROKES} strokes do not mix a well."
    return "A stroke of the whole well draws air at the bottom and foams the liquid."


def _fix(mix: _Mix, capped: Pipette | None) -> str:
    if capped is not None and PIPETTE_TOO_SMALL in mix.reasons:
        bigger = _smallest_that_mixes(mix.well_ul)
        if bigger is None:
            return (
                "No OT-2 pipette draws a fifth of this well: mix it off the robot, or split it "
                "into smaller wells."
            )
        name, max_ul = bigger
        good = round(min(GOOD_SHARE * mix.well_ul, max_ul), 1)
        return (
            f"Mix with a bigger pipette (a {name} for this well): at least {GOOD_STROKES} "
            f"strokes of {good:g} ul, `mix({GOOD_STROKES}, {good:g}, well)`."
        )
    if capped is not None:
        return (
            f"Mix with the pipette's full volume ({capped.max_volume_ul:g} ul) at least "
            f"{GOOD_STROKES} times: `mix({GOOD_STROKES}, {capped.max_volume_ul:g}, well)`, or use "
            "a bigger pipette."
        )
    good = round(GOOD_SHARE * mix.well_ul, 1)
    return (
        f"Mix the well with about 80% of its volume ({good:g} ul) at least {GOOD_STROKES} times: "
        f"`mix({GOOD_STROKES}, {good:g}, well)`. A stroke of the whole well draws air; use no "
        "more than 90%."
    )


def _smallest_that_mixes(well_ul: float) -> tuple[str, float] | None:
    """The smallest OT-2 GEN2 pipette whose maximum is at least a fifth of the well."""
    return next((p for p in OT2_PIPETTES if p[1] >= CAP_SHARE * well_ul - 1e-9), None)


def _label(pipette: Pipette) -> str:
    """ "P20" from "p20_single_gen2"."""
    return pipette.name.split("_")[0].upper()


def _range(values: Iterable[float]) -> str:
    """ "30" when every value agrees; "30 to 60" otherwise."""
    seen = sorted({float(v) for v in values})
    if len(seen) == 1:
        return f"{seen[0]:g}"
    return f"{seen[0]:g} to {seen[-1]:g}"


RULE = Rule(
    rule_id=RULE_ID,
    family=3,
    tier="structural",
    title=TITLE,
    description=(
        "A run of mixing strokes that cannot mix the well. A mix counts only if the strokes "
        "together move about two wells' worth of liquid (the number is in the rulebook), there "
        "are at least three of them, and no stroke is the whole well. Warning. Silent on a well "
        "of unknown volume, a well holding one liquid (a pre-wet), a stock only drawn from, and "
        "a single stroke followed by a draw from the same well (a prime). When the well holds "
        "more than the pipette can draw, the strokes are measured against the pipette instead, "
        "and a pipette that cannot draw a fifth of the well fires whatever the count."
    ),
    sources=(
        sources.INTEGRA_SERIAL_DILUTION,
        sources.INTEGRA_SERIAL_DILUTION_PROTOCOLS,
        sources.BECKMAN_AMPURE,
        sources.ESCA_SERIAL_DILUTION,
        sources.LABAUTOMATION_3654,
        sources.ARTEL_SOURCES_OF_ERROR,
    ),
    check=check,
)
