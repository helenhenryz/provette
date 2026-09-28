"""The findings as JSON. The schema is `provette.rules.finding`; `schema_version` says which."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from provette.rules import RULES, SCHEMA_VERSION, Finding
from provette.rules.roles import unplaced

if TYPE_CHECKING:
    from provette.check import CheckResult


def counts(findings: list[Finding] | tuple[Finding, ...]) -> dict[str, dict[str, int]]:
    return {
        "by_severity": dict(Counter(f.severity for f in findings)),
        "by_rule": dict(Counter(f.rule_id for f in findings)),
    }


def report_json(result: CheckResult) -> dict[str, Any]:
    deck = result.trace.deck
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol": result.path.name,
        "api_level": deck.api_level,
        "simulator": {"passed": True, "opentrons_version": deck.opentrons_version},
        "rules": [
            {"rule_id": r.rule_id, "family": r.family, "tier": r.tier, "description": r.description}
            for r in RULES
        ],
        "counts": counts(result.findings),
        "findings": [finding.to_json() for finding in result.findings],
        # declared liquids no word list knows: the product asks the student what they are
        "unplaced_liquids": [u.to_json() for u in unplaced(result.trace)],
    }
