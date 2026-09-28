"""The finding: one biology problem in one protocol, in a shape that does not change.

The text report, the JSON report, the agent that patches protocols and the web replay all read
this and nothing else. Everything is a frozen value and turns into plain JSON with `to_json`.
Adding a field is fine; renaming or removing one means raising `SCHEMA_VERSION`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

SCHEMA_VERSION = 1

Tier = Literal["structural", "role"]
Severity = Literal["error", "warning", "note"]
RolesBasis = Literal["none", "declared", "inferred"]

SEVERITY_ORDER: dict[str, int] = {"error": 0, "warning": 1, "note": 2}


@dataclass(frozen=True)
class Source:
    """What a rule rests on. Copied from docs/rule-sources.md, never invented."""

    name: str
    url: str


@dataclass(frozen=True, order=True)
class WellRef:
    """A well, with enough around it to show it to a person.

    `labware_id` and `well` identify it in the trace. `liquid` is the name the protocol declared
    for what the well held at the start, or None.
    """

    labware_id: str
    well: str
    slot: str
    labware: str  # the label the author gave the labware, else its display name
    liquid: str | None = None

    @property
    def key(self) -> str:
        return f"{self.labware_id}[{self.well}]"


@dataclass(frozen=True)
class Occurrence:
    """One time the root line did the damage. A loop gives many of these, and one finding."""

    event_index: int
    line: int | None


@dataclass(frozen=True)
class Downstream:
    """Every other well the damage later reached. `count == len(wells)`."""

    count: int
    wells: tuple[WellRef, ...]


@dataclass(frozen=True)
class Finding:
    rule_id: str  # "CONTAM-STOCK"
    family: int  # the row of the family table in docs/rule-sources.md
    tier: Tier
    severity: Severity
    certain: bool  # False when it rests on a contact the model could not decide
    roles_basis: RolesBasis  # structural rules: "none"
    title: str
    explanation: str  # what happened, where, and why it matters
    fix: str  # what would fix it
    line: int | None  # the line of the root event, in the file that was checked
    stack: tuple[str, ...]  # protocol frames of the root event, outermost first: "run:41"
    occurrences: tuple[Occurrence, ...]
    wells: tuple[WellRef, ...]  # the wells directly affected
    downstream: Downstream
    sources: tuple[Source, ...]
    fingerprint: str = ""  # filled in by `provette.rules.run_rules`

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


RANK: dict[str, int] = {"note": 0, "warning": 1, "error": 2}


def lower(severity: Severity) -> Severity:
    """One level down: what an uncertain contact does to a finding."""
    return "warning" if severity == "error" else "note"


def fingerprint(finding: Finding, source_lines: Sequence[str] | None) -> str:
    """A short hash that names this finding across edits to the protocol.

    It is made of the rule, the *text* of the root line (and of the lines that called it, if the
    root is inside a helper function), and the affected wells. Line numbers and event numbers
    are left out on purpose: adding a comment at the top of the file moves every line and must
    not orphan our triage labels. If two lines of the file have the same text, the
    position among those twins is added, so they stay distinct.

    With no source text to read, the line number is used instead.
    """
    parts = [finding.rule_id]
    frames = finding.stack or ((f"?:{finding.line}",) if finding.line is not None else ())
    for frame in frames:
        function, _, number = frame.rpartition(":")
        line = int(number) if number.isdigit() else None
        parts.append(function)
        parts.append(_line_identity(line, source_lines))
    parts.extend(sorted(well.key for well in finding.wells))
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:12]


def _line_identity(line: int | None, source_lines: Sequence[str] | None) -> str:
    if line is None:
        return "?"
    if source_lines is None or not 1 <= line <= len(source_lines):
        return f"#{line}"
    text = source_lines[line - 1].strip()
    twins_before = sum(other.strip() == text for other in source_lines[: line - 1])
    return f"{text}\x1e{twins_before}"
