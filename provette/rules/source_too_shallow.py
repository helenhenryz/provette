"""SOURCE-TOO-SHALLOW: the tip aspirates above the liquid, so the pipette draws air.

In words. Opentrons aspirates 1 mm above the bottom of the well unless told otherwise. That is
fine in a tube, where a cone lifts even 20 ul above the tip; it is not fine in a wide, flat
vessel: 2 ml of master mix in a 195 ml reservoir is 1.2 mm deep, and after 46 draws of 18 ul
the surface is below the tip. The pipette then draws air, every well filled from those draws
is short of the reagent, and the simulator says nothing, because it does not track liquid.
Once the surface is below the tip nothing more leaves the well, so every later draw at that
height is air too: the finding counts them all.

The rule reads the replay: an aspirate whose tip is above the liquid's surface, in a well whose
height is known (the labware definition's shape is in the trace, or its bottom is flat), is a
certain air draw. One finding per line of the protocol: the well, what it held, how high that
reaches, where the tip was, how much air was drawn, and the wells that got air instead.

What it does not fire on:

* an `air_gap`, or an aspirate written by hand in the top half of the well (an air gap by hand);
* an air gap by hand at any height: an aspirate above the liquid that is followed at once, with
  the same tip and no other move of that tip in between, by another aspirate from the same
  well, whether or not that one reaches the liquid. The first draw of the pair was meant to be
  air either way (the flood read's false alarm was `aspirate(2, s.bottom(5))  # pre-airgap`,
  then the real draw at the same height; the second draw is reported on its own if it is air);
* a well whose shape is unknown: the replay calls the contact uncertain and the rule is silent;
* a protocol that declares no liquids: a well the robot filled may have arrived full, so its
  volume is not trusted;
* a well that holds no more than the draw asks for: the prep sheet already says that well
  "would run dry" or has "no margin", and the rule does not say it twice (the audit's two
  repeats were tubes declared at exactly what the run needs);
* a well that is running out (drawn down to a tenth or less of the most it held before the
  tip first came up dry): that is the prep sheet's "would run dry" or "no margin" flag, not a
  shallow source;
* `well.bottom(x)` with x below the surface: the tip is in the liquid, nothing to report.
"""

from __future__ import annotations

from dataclasses import dataclass

from provette.intent.prep import NO_MARGIN
from provette.model import Event, Trace, WellKey
from provette.rules import sources
from provette.rules.common import (
    facts_of,
    natural,
    place,
    stack_key,
    times,
    well_listing,
    well_with_liquid,
)
from provette.rules.finding import Downstream, Finding
from provette.rules.rule import Rule
from provette.state import Contact, Run
from provette.state.contact import CONTACT_TOLERANCE_MM, volume_at_mm

RULE_ID = "SOURCE-TOO-SHALLOW"
HAND_AIR_GAP_SHARE = 0.5  # an aspirate this high up the well, or higher, is an air gap by hand


@dataclass(frozen=True)
class _Draw:
    """One channel of one aspirate that drew air because the liquid was below the tip."""

    event: Event
    contact: Contact
    held_ul: float  # what the well held as the event began
    fed: tuple[WellKey, ...]  # where this tip dispensed before it next drew


def check(trace: Trace, run: Run) -> list[Finding]:
    if not trace.deck.liquid_loads:
        return []
    facts = facts_of(trace, run)
    geometry = {
        WellKey(lw.labware_id, name): well
        for lw in trace.deck.labware
        for name, well in lw.wells.items()
    }
    peaks = _Peaks(run)
    groups: dict[tuple[str, ...], list[_Draw]] = {}
    for event, step in zip(trace.events, run.steps, strict=True):
        if event.op != "aspirate" or event.parent == "air_gap" or not event.volume_ul:
            continue
        for contact in step.contacts:
            if contact.reason != "tip_above_surface" or contact.tip is None:
                continue
            well = geometry.get(contact.well)
            height = contact.tip_height_mm
            if well is None or height is None or height > HAND_AIR_GAP_SHARE * well.depth_mm:
                continue  # an aspirate high in the well is an air gap written by hand
            held = run.well_before(contact.well, event.index).volume_ul
            if held is None or held <= event.volume_ul:
                continue  # the well holds no more than the draw: the prep sheet's flag
            if held <= (1 - NO_MARGIN) * peaks.before(contact.well, event.index):
                continue  # the well is running out: the prep sheet's flag
            if _air_gap_by_hand(run, trace, event.index, contact.tip, contact.well):
                continue  # the real draw comes straight after: this one was meant to be air
            fed = _fed(run, trace, event.index, contact.tip, contact.well)
            groups.setdefault(stack_key(event), []).append(_Draw(event, contact, held, fed))

    findings = []
    pipettes = {p.mount: p for p in trace.deck.pipettes}
    for key, draws in groups.items():
        first = draws[0]
        pipette = pipettes.get(first.event.mount) if first.event.mount else None
        pipette_name = pipette.name if pipette else "the pipette"
        source_wells = facts.refs(d.contact.well for d in draws)
        source = facts.ref(first.contact.well)
        well = geometry[first.contact.well]
        labware = next(lw for lw in trace.deck.labware if lw.labware_id == source.labware_id)
        sources_drawn = {d.contact.well for d in draws}
        got_air = sorted({w for d in draws for w in d.fed} - sources_drawn, key=natural)
        air = sum(d.contact.air_ul for d in draws)
        in_liquid = _draws_in_liquid_before(run, trace, key, first.event.index)
        tip_mm = first.contact.tip_height_mm or 0.0
        surface = first.contact.surface_mm or 0.0
        needs = volume_at_mm(well, tip_mm + CONTACT_TOLERANCE_MM)

        what = (
            f"At line {first.event.line} the {pipette_name} draws {first.event.volume_ul:g} ul "
            f"from {well_with_liquid(source)} with its tip {tip_mm:g} mm above the bottom of "
            f"the well. By then the well holds {first.held_ul:,.0f} ul, which in this "
            f"{labware.display_name} reaches only {surface:.2f} mm up: the tip is above the "
            f"liquid and draws air"
        )
        if len(draws) > 1 or in_liquid:
            what += f" (this line did it {times(len(draws))}"
            if in_liquid:
                what += f", after {times(in_liquid)} in the liquid"
            what += f"; {air:,.0f} ul of air in all)"
        what += ". The simulator does not notice: it does not follow the liquid."
        mixing = first.event.parent == "mix" or not got_air
        if mixing:
            what += " These are mixing strokes: the tip stirs air, and the well is not mixed."
        else:
            what += (
                f" The {len(got_air)} {'well' if len(got_air) == 1 else 'wells'} filled from "
                "these draws got air instead of liquid."
            )
        if len(source_wells) > 1:
            what += f" Source wells: {well_listing(source_wells)}."

        deeper = (
            f" This well needs about {needs:,.0f} ul in it for the surface to reach {tip_mm:g} mm."
            if needs is not None
            else ""
        )
        fix = (
            f"Mix lower, with `well.bottom(0.5)`, so the tip is in the liquid.{deeper}"
            if mixing
            else f"Keep the liquid above the tip.{deeper} Load that much more than the run "
            "draws; or draw from a smaller vessel (a tube lifts the liquid); or aspirate "
            "lower with `well.bottom(0.5)`."
        )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity="error",
                certain=True,
                roles_basis="none",
                title=f"The pipette draws air from {place(source)}: the liquid is below the tip",
                explanation=what,
                fix=fix,
                line=first.event.line,
                stack=tuple(first.event.stack),
                occurrences=facts.occurrences(d.event.index for d in draws),
                wells=source_wells,
                downstream=Downstream(len(got_air), facts.refs(got_air)),
                sources=RULE.sources,
            )
        )
    return findings


class _Peaks:
    """The most a well has held up to a given event: what "running out" is measured against."""

    def __init__(self, run: Run) -> None:
        self._run = run
        self._by_well: dict[WellKey, list[tuple[int, float]]] = {}

    def before(self, well: WellKey, event_index: int) -> float:
        if well not in self._by_well:
            initial = self._run.initial_wells[well].volume_ul or 0.0
            rows, top = [], initial
            for index, state in self._run.history.get(well, []):
                top = max(top, state.volume_ul or 0.0)
                rows.append((index, top))
            self._by_well[well] = rows
        peak = self._run.initial_wells[well].volume_ul or 0.0
        for index, top in self._by_well[well]:
            if index >= event_index:
                break
            peak = top
        return peak


def _fed(
    run: Run, trace: Trace, event_index: int, tip: WellKey, source: WellKey
) -> tuple[WellKey, ...]:
    """The wells this tip dispensed into after the draw and before it next drew or was dropped."""
    fed: list[WellKey] = []
    for step in run.steps[event_index + 1 :]:
        event = trace.events[step.event_index]
        if step.op == "drop_tip" and any(t.tip == tip for t in event.targets):
            break
        if step.op not in ("aspirate", "dispense", "blow_out"):
            continue
        mine = [c for c in step.contacts if c.tip == tip]
        if not mine:
            continue
        if step.op == "aspirate":
            break
        fed += [c.well for c in mine if c.well != source and c.well not in fed]
    return tuple(fed)


def _air_gap_by_hand(run: Run, trace: Trace, event_index: int, tip: WellKey, well: WellKey) -> bool:
    """Is this tip's very next move another aspirate from the same well?

    Then the air draw before it was an air gap written by hand, at whatever height, whether or
    not the second draw reaches the liquid (if it does not, it is reported on its own). Events
    that do not involve this tip (a delay, the other pipette) are not moves of it.
    """
    for step in run.steps[event_index + 1 :]:
        event = trace.events[step.event_index]
        if event.op == "other" or not any(t.tip == tip for t in event.targets):
            continue
        if event.op != "aspirate":
            return False
        mine = [c for c in step.contacts if c.tip == tip]
        return bool(mine) and all(c.well == well for c in mine)
    return False


def _draws_in_liquid_before(run: Run, trace: Trace, key: tuple[str, ...], event_index: int) -> int:
    """How many aspirates of the same line reached the liquid before the first one that did not."""
    count = 0
    for event, step in zip(trace.events[:event_index], run.steps[:event_index], strict=True):
        if event.op == "aspirate" and stack_key(event) == key:
            count += sum(c.verdict == "contact" for c in step.contacts)
    return count


RULE = Rule(
    rule_id=RULE_ID,
    family=9,
    tier="structural",
    title="The source is too shallow for the tip",
    description=(
        "An aspirate whose tip is above the liquid in a well of known shape draws air: every "
        "well filled from it is short. The simulator does not notice."
    ),
    sources=(
        sources.OPENTRONS_LIQUID_CONTROL,
        sources.ARTEL_SOURCES_OF_ERROR,
        sources.GILSON_GUIDE,
        sources.LABAUTOMATION_ASPIRATING_AIR,
        sources.INTEGRA_DEAD_VOLUME,
    ),
    check=check,
)
