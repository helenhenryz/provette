"""The rules: each one a plain function `(trace, run) -> list[Finding]`. See README.md here.

No plug-ins and no configuration: the rules that run are the ones in `RULES` below: the
rules written in Python, then the declared rules read from `declared/*.yaml` (`declared.py`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from provette.model import Trace
from provette.rules import (
    cold_module,
    contam_stock,
    contam_well,
    declared,
    mix_before_draw,
    mix_too_weak,
    negative_control,
    pipette_range,
    source_too_shallow,
    unmixed_at_end,
    well_capacity,
)
from provette.rules.finding import (
    SCHEMA_VERSION,
    SEVERITY_ORDER,
    Downstream,
    Finding,
    Occurrence,
    Source,
    WellRef,
    fingerprint,
)
from provette.rules.rule import Rule, RuleWithoutSource
from provette.state import Run

RULES: list[Rule] = [
    contam_stock.RULE,
    contam_well.RULE,
    mix_before_draw.RULE,
    mix_too_weak.RULE,
    pipette_range.RULE,
    well_capacity.RULE,
    source_too_shallow.RULE,
    cold_module.RULE,
    unmixed_at_end.RULE,
    negative_control.RULE,
]
RULES += declared.load_rules(taken=[rule.rule_id for rule in RULES])


def run_rules(trace: Trace, run: Run, source_lines: Sequence[str] | None = None) -> list[Finding]:
    """Every rule's findings, fingerprinted, worst first and then in file order.

    `source_lines` is the text of the protocol file, line by line. The fingerprint is made from
    the text of the root line so that it survives edits elsewhere in the file; without the text
    it falls back to the line number.
    """
    findings = [finding for rule in RULES for finding in rule.check(trace, run)]
    findings = [replace(f, fingerprint=fingerprint(f, source_lines)) for f in findings]
    return sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.line or 0, f.rule_id))


__all__ = [
    "RULES",
    "SCHEMA_VERSION",
    "Downstream",
    "Finding",
    "Occurrence",
    "Rule",
    "RuleWithoutSource",
    "Source",
    "WellRef",
    "run_rules",
]
