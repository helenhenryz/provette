"""The report a student reads in a terminal: a verdict, then each finding, then the simulator."""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from typing import TYPE_CHECKING

from provette.rules import Finding
from provette.rules.common import well_listing
from provette.rules.roles import unplaced

if TYPE_CHECKING:
    from provette.check import CheckResult

WIDTH = 92


def report_text(result: CheckResult) -> str:
    findings = result.findings
    name = result.path.name
    out: list[str] = []
    if not findings:
        out.append(f"{name}: no biology problems found.")
    else:
        tally = ", ".join(
            f"{n} {severity}{'s' if n > 1 else ''}"
            for severity in ("error", "warning", "note")
            if (n := sum(f.severity == severity for f in findings))
        )
        out.append(f"{name}: {len(findings)} biology problem{'s' if len(findings) > 1 else ''}")
        out[-1] += f" ({tally})."
    for number, finding in enumerate(findings, 1):
        out += ["", *finding_lines(number, finding, result.source_lines)]
    deck = result.trace.deck
    out += [
        "",
        f"The Opentrons simulator ({deck.opentrons_version}) passed this protocol with no error:"
        " it checks that the robot can make the moves, not what they do to the liquids.",
    ]
    if not findings:
        out.append("A clean report is not a promise that the experiment will work.")
    for liquid in unplaced(result.trace):
        out += ["", liquid.sentence]
    return "\n".join(_wrap(line) for line in out) + "\n"


def finding_lines(number: int, finding: Finding, source_lines: Sequence[str]) -> list[str]:
    """One finding as the terminal shows it; `provette verify` prints its findings the same way."""
    unsure = "" if finding.certain else ", not certain"
    out = [f"{number}. {finding.severity.upper()} {finding.rule_id}{unsure}: {finding.title}"]
    if finding.line is not None and 1 <= finding.line <= len(source_lines):
        out.append(f"   line {finding.line}:  {source_lines[finding.line - 1].strip()}")
    if len(finding.stack) > 1:
        out.append(f"   reached through: {' > '.join(finding.stack)}")
    out.append(f"   {finding.explanation}")
    out.append(f"   Affected: {well_listing(finding.wells)}.")
    if finding.downstream.count:
        out.append(
            f"   Also reached {finding.downstream.count} other "
            f"well{'s' if finding.downstream.count > 1 else ''}: "
            f"{well_listing(finding.downstream.wells)}."
        )
    out.append(f"   Fix: {finding.fix}")
    for source in finding.sources:
        out.append(f"   Source: {source.name}")
        out.append(f"           {source.url}")
    out.append(f"   [{finding.fingerprint}]")
    return out


def _wrap(line: str) -> str:
    if len(line) <= WIDTH or "http" in line or line.lstrip().startswith("line "):
        return line
    indent = " " * (len(line) - len(line.lstrip()))
    return textwrap.fill(line, WIDTH, initial_indent="", subsequent_indent=indent)
