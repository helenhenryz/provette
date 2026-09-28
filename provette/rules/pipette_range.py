"""PIPETTE-RANGE: a pipette is asked for a volume below what it can measure.

In words. Every pipette has a range. Below its minimum it cannot draw the volume at all, or
draws it so inaccurately that the number in the script is fiction: a p300 asked for 5 ul may
deliver anything. The simulator does not care; it passes the move. The volumes then add up on
paper and the plate map is "satisfied", which is why this rule exists: it is the one thing that
can turn a verified protocol into a wrong one that nobody sees.

An aspirate at less than the pipette's minimum volume is an error. Nothing is said about
volumes that are legal but low in the range: Integra's "work at 35 to 100% of nominal" is
advice for hand pipettes, and drawing exactly the minimum (20 ul of master mix with a p300) is
so common in real protocols that a note on it would flood every report.

Air gaps are not liquid and are not judged. A mix is judged like any aspirate. A dispense of what
the tip holds after a bigger aspirate (a distribute) is judged on the aspirate, not on the parts.
"""

from __future__ import annotations

from provette.model import Event, Trace
from provette.rules import sources
from provette.rules.common import facts_of, listing, stack_key, times, well_listing
from provette.rules.finding import Downstream, Finding, Severity
from provette.rules.rule import Rule
from provette.state import Run

RULE_ID = "PIPETTE-RANGE"


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    pipettes = {p.mount: p for p in trace.deck.pipettes}
    # (severity, stack key) -> events, so one line in a loop is one finding
    groups: dict[tuple[Severity, tuple[str, ...]], list[Event]] = {}
    for event in trace.events:
        if event.op != "aspirate" or event.parent == "air_gap" or event.mount is None:
            continue
        pipette = pipettes.get(event.mount)
        volume = event.volume_ul
        if pipette is None or volume is None or volume <= 0:
            continue
        if volume >= pipette.min_volume_ul:
            continue
        groups.setdefault(("error", stack_key(event)), []).append(event)

    findings = []
    for (severity, _key), events in groups.items():
        first = events[0]
        pipette = pipettes[first.mount or "left"]
        volumes = sorted({e.volume_ul for e in events if e.volume_ul is not None})
        wells = facts.refs(t.well for e in events for t in e.targets)
        shown = listing([f"{v:g} ul" for v in volumes])
        what = (
            f"At line {first.line} the {pipette.name} is asked to draw {shown}, below its "
            f"minimum of {pipette.min_volume_ul:g} ul"
            f"{'' if len(events) == 1 else f' (this line did it {times(len(events))})'}. "
            "A pipette cannot measure less than its minimum: it draws the wrong amount, or "
            "nothing, and the volumes in this protocol only add up on paper. The simulator "
            "passes the move."
        )
        fix = (
            "Use a pipette whose range covers the volume (a p20 for 1 to 20 ul), or scale "
            "the reaction so every volume is at least the pipette's minimum."
        )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity=severity,
                certain=True,
                roles_basis="none",
                title=(
                    f"{shown} {'is' if len(volumes) == 1 else 'are'} below what the "
                    f"{pipette.name} can measure ({pipette.min_volume_ul:g} ul at least)"
                ),
                explanation=what + f" Wells: {well_listing(wells)}.",
                fix=fix,
                line=first.line,
                stack=tuple(first.stack),
                occurrences=facts.occurrences(e.index for e in events),
                wells=wells,
                downstream=Downstream(0, ()),
                sources=RULE.sources,
            )
        )
    return findings


RULE = Rule(
    rule_id=RULE_ID,
    family=4,
    tier="structural",
    title="Volume outside the pipette's range",
    description=(
        "An aspirate below the pipette's minimum volume is an error: the amount cannot be "
        "measured, and the simulator does not notice."
    ),
    sources=(sources.OPENTRONS_PIPETTES, sources.INTEGRA_PIPETTING_TIPS),
    check=check,
)
