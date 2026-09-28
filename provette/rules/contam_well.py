"""CONTAM-WELL: a used tip left in a well a liquid that the protocol never puts there.

In words. A tip that has been in liquid X touches the liquid of a well, and at no point in the
whole run does the protocol transfer X into that well on purpose. So X was never meant to be
there. This is what happens when one tip adds a reagent to a row of different samples and
touches each of them: every well gets a little of the wells before it.

What it must NOT flag, because a naive version flagged 117 of 150 public protocols:
replicates that hold the same liquids; a serial dilution with one tip (the liquid is carried
down the row on purpose); mixing in a well the tip has just dispensed into; one tip filling
many wells from above the liquid. `tests/fixtures/rules/CONTAM-WELL/near_miss_*.py`.

The severity is a warning: without knowing what the wells hold, Provette cannot say how bad the
mix-up is. The role-based sample rule (family 2) raises it when both are samples.
"""

from __future__ import annotations

from provette.model import Trace
from provette.rules import sources
from provette.rules.common import (
    ALIKE_NOTE,
    facts_of,
    group_by_line,
    liquid,
    listing,
    times,
    well_listing,
)
from provette.rules.finding import RANK, Downstream, Finding, lower
from provette.rules.rule import Rule
from provette.state import Run

RULE_ID = "CONTAM-WELL"
TITLE = "A used tip carried liquid into wells it was never meant for"


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    roots = [
        a
        for a in facts.roots
        if not facts.is_stock(a.well) and a.atom != a.well and not facts.deliberate(a.well, a.atom)
    ]
    findings = []
    for group in group_by_line(facts, roots):
        first = facts.event(group[0].event_index)
        wells = facts.refs(a.well for a in group)
        carried = facts.refs(a.atom for a in group)
        touched = {a.well for a in group}
        reached = facts.refs(w for w in facts.consequences(group) if w not in touched)
        certain = any(a.certain for a in group)
        severity = max(
            (facts.carry_severity(a.atom, a.well, "warning") for a in group), key=RANK.__getitem__
        )
        roles_known = any(facts.role(a.atom) is not None for a in group)
        if not certain:
            severity = lower(severity)
        alike = all(facts.treated_alike(a) for a in group)
        if alike:
            severity = "note"
        count = len({a.event_index for a in group})

        explanation = (
            f"At line {first.line} the tip touched the liquid in {well_listing(wells)} while it "
            f"still carried {listing([liquid(c) for c in carried])} from an earlier step"
            f"{'' if count == 1 else f' (this line did it {times(count)})'}. "
            "A tip that has touched one liquid leaves a little of it in the next liquid it "
            "touches. The protocol never transfers that liquid into "
            f"{'this well' if len(wells) == 1 else 'these wells'} on purpose, so it was not "
            "meant to be there. If the wells hold different samples, each now holds a little "
            "of another."
        )
        if reached:
            explanation += (
                f" Liquid was later taken out of the affected wells, and the unwanted material "
                f"went along into {len(reached)} other well{'s' if len(reached) > 1 else ''}: "
                f"{well_listing(reached)}."
            )
        if alike:
            explanation += ALIKE_NOTE
        if not certain:
            explanation += (
                " Provette could not tell for sure that the tip touched the liquid here "
                "(it does not know how full the well was), so this is reported one level lower."
            )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity=severity,
                certain=certain,
                roles_basis="inferred" if roles_known else "none",
                title=(
                    f"A used tip carried {listing([liquid(c) for c in carried])} into "
                    f"{well_listing(wells) if len(wells) == 1 else f'{len(wells)} wells'} "
                    "it was never meant for"
                ),
                explanation=explanation,
                fix=(
                    f"Use a fresh tip for each well at line {first.line}. If one tip must serve "
                    "many wells, dispense from above the liquid (for example `well.top()`) so "
                    "that the tip never touches what is already in the well."
                ),
                line=first.line,
                stack=tuple(first.stack),
                occurrences=facts.occurrences(a.event_index for a in group),
                wells=wells,
                downstream=Downstream(len(reached), reached),
                sources=RULE.sources,
            )
        )
    return findings


RULE = Rule(
    rule_id=RULE_ID,
    family=1,
    tier="structural",
    title=TITLE,
    description=(
        "A tip that has been in a liquid touches the liquid of a well into which the protocol "
        "never transfers that liquid on purpose, before or after. Warning."
    ),
    sources=(sources.LAB_MANAGER_CARRY_OVER,),
    check=check,
)
