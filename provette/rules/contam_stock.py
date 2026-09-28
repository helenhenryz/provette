"""CONTAM-STOCK: a used tip went into a stock and left another liquid in it.

In words. A *stock* is a well the protocol draws liquid from and that held liquid before the
robot put any there: a reagent tube, a sample tube, a reservoir channel. If a tip that has been
in some other liquid dips into a stock, a little of that other liquid stays behind. If the
protocol keeps drawing from the stock, the trace goes wherever the stock goes.

It does not fire when both liquids were declared under the same name (water from two tubes is
still water), or when the protocol also puts that liquid into the stock on purpose.
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
    well_with_liquid,
)
from provette.rules.finding import RANK, Downstream, Finding, Severity, lower
from provette.rules.rule import Rule
from provette.state import Run

RULE_ID = "CONTAM-STOCK"
TITLE = "A used tip went into a stock"


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    roots = [
        a
        for a in facts.roots
        if facts.is_stock(a.well) and a.atom != a.well and not facts.deliberate(a.well, a.atom)
    ]
    findings = []
    for group in group_by_line(facts, roots):
        first = facts.event(group[0].event_index)
        stocks = facts.refs(a.well for a in group)
        carried = facts.refs(a.atom for a in group)
        reached = facts.refs(facts.consequences(group))
        first_hit: dict[object, int] = {}
        for a in group:
            first_hit.setdefault(a.well, a.event_index)
        drawn_again = any(facts.drawn_after(a.well, first_hit[a.well]) for a in group)
        certain = any(a.certain for a in group)

        severity: Severity = "error" if reached else "warning"
        # What was carried decides how much it matters: water into a stock is a note, a sample
        # into the master mix is what it is. The worst pair in the group sets the finding.
        by_role = max(
            (facts.carry_severity(a.atom, a.well, severity) for a in group), key=RANK.__getitem__
        )
        roles_known = any(facts.role(a.atom) is not None for a in group)
        severity = by_role
        if not certain:
            severity = lower(severity)
        alike = all(facts.treated_alike(a) for a in group)
        if alike:
            severity = "note"

        stock_words = well_with_liquid(stocks[0]) if len(stocks) == 1 else f"{len(stocks)} stocks"
        count = len({a.event_index for a in group})
        it = "it" if len(stocks) == 1 else "them"
        explanation = (
            f"At line {first.line} the tip went into "
            f"{listing([well_with_liquid(s) for s in stocks])} while it still carried "
            f"{listing([liquid(c) for c in carried])} from an earlier step"
            f"{'' if count == 1 else f' (this line did it {times(count)})'}. "
            "A tip that has touched one liquid leaves a little of it in the next liquid it "
            f"touches, so {'this stock now holds' if len(stocks) == 1 else 'these stocks now hold'}"
            " material that does not belong there. "
        )
        if reached:
            explanation += (
                f"Liquid drawn from {it} then took the unwanted material along into "
                f"{len(reached)} other well{'s' if len(reached) > 1 else ''}: "
                f"{well_listing(reached)}."
            )
        elif drawn_again:
            explanation += (
                f"The protocol drew from {it} again afterwards, but only into wells that were "
                "given that material on purpose anyway, so this run is not harmed. What is "
                "left in the stock is no longer clean for the next run."
            )
        else:
            explanation += (
                f"The protocol does not draw from {it} again, so this run is not harmed, but "
                "what is left in the stock is no longer clean for the next run."
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
                title=f"{TITLE}: {stock_words}",
                explanation=explanation,
                fix=(
                    f"Pick up a fresh tip before line {first.line} goes into the stock. Or change "
                    "the order: hand out the shared liquid first, while the tip is still clean, "
                    "and add the other liquids afterwards with a fresh tip each."
                ),
                line=first.line,
                stack=tuple(first.stack),
                occurrences=facts.occurrences(a.event_index for a in group),
                wells=stocks,
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
        "A tip that has been in another liquid touches the liquid of a stock (a well that held "
        "liquid from the start and that the protocol draws from). Error if the stock is drawn "
        "from again and the trace reaches wells it was never meant for; warning otherwise."
    ),
    sources=(sources.LAB_MANAGER_CARRY_OVER, sources.WHO_MASTER_MIX),
    check=check,
)
