"""The verification as a student reads it in a terminal, and as JSON."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Any

from provette.intent.accounting import Accounting
from provette.intent.compare import IntentReport, Issue, WellResult
from provette.intent.prep import PrepLine, PrepSheet
from provette.intent.spec import PlateMap
from provette.report.text import finding_lines
from provette.rules.finding import Finding
from provette.rules.roles import Unplaced

WIDTH = 92
MOST_WELLS = 12  # mismatching wells printed in full; the rest are counted


@dataclass(frozen=True)
class Verification:
    protocol_name: str
    platemap: PlateMap
    intent: IntentReport
    accounting: Accounting
    prep: PrepSheet
    labware: tuple[Finding, ...] = ()  # LABWARE-FOR-TECHNIQUE (provette/intent/labware.py)
    source_lines: tuple[str, ...] = ()  # the protocol's text, so a finding can quote its line
    unplaced: tuple[Unplaced, ...] = ()  # declared liquids no word list knows (roles.yaml)

    @property
    def labware_failed(self) -> bool:
        """A labware finding of severity error or warning (a note does not fail)."""
        return any(f.severity in ("error", "warning") for f in self.labware)

    @property
    def exit_code(self) -> int:
        """0 all verified, 1 a mismatch, a flag or a labware warning, 3 the map could not be
        checked."""
        if self.intent.status == "cannot_check":
            return 3
        flagged = self.accounting.flagged or self.prep.flagged or self.labware_failed
        return 1 if self.intent.status == "mismatch" or flagged else 0


def _ul(volume: float) -> str:
    return f"{volume:.2f}".rstrip("0").rstrip(".") + " ul"


def _contents(contents: Any) -> str:
    return ", ".join(f"{_ul(v)} {k}" for k, v in contents.items() if k != "?") or "nothing"


def _issue(issue: Issue) -> str:
    if issue.kind == "wrong_amount":
        return (
            f"wrong amount of {issue.liquid}: the plate map says {_ul(issue.expected_ul or 0)}, "
            f"the protocol delivers {_ul(issue.found_ul or 0)}"
        )
    if issue.kind == "missing_liquid":
        want = _ul(issue.expected_ul or 0)
        return f"{issue.liquid} is missing: the plate map says {want}, none arrives"
    if issue.kind == "unexpected_liquid":
        return (
            f"holds {_ul(issue.found_ul or 0)} of {issue.liquid}, which the plate map does not "
            "list for this well"
        )
    if issue.kind == "well_empty":
        return "the well is empty at the end" + (f" ({issue.detail})" if issue.detail else "")
    if issue.kind == "no_well":
        return "no well on the plate holds this"
    if issue.kind == "unexpected_well":
        return "the plate map says nothing about this well, but it holds liquid"
    if issue.kind == "wrong_position":
        return f"in the wrong well: {issue.detail}"
    return f"the amount cannot be known: {issue.detail}"


def _well_lines(result: WellResult) -> list[str]:
    where = f"well {result.well}" if result.well else "nowhere"
    of = f" ({result.group})" if result.group else ""
    out = [f"  {where}{of}: expected {_contents(result.expected)}; found {_contents(result.found)}"]
    out += [f"      - {_issue(issue)}" for issue in result.issues]
    return out


def report_text(v: Verification) -> str:
    intent = v.intent
    out: list[str] = []
    if intent.status == "cannot_check":
        out.append(f"{v.protocol_name}: CANNOT CHECK against plate map {v.platemap.id}.")
        out += [f"  {problem}" for problem in intent.problems]
        out.append("  Nothing was verified. This is not a pass.")
    else:
        n_ok = sum(r.ok for r in intent.wells)
        verdict = "VERIFIED" if intent.status == "verified" else "MISMATCH"
        out.append(
            f"{v.protocol_name}: {verdict} against plate map {v.platemap.id}. "
            f"{n_ok} of {len(intent.wells)} wells hold what the plate map says."
        )
        out.append(
            f"  Destination: {intent.destination_name}. Reading of the request: {intent.variant}."
        )
        bad = intent.mismatches
        for result in bad[:MOST_WELLS]:
            out += _well_lines(result)
        if len(bad) > MOST_WELLS:
            out.append(f"  ... and {len(bad) - MOST_WELLS} more wells that do not match.")
    out += [f"  Note: {note}" for note in intent.notes]

    if v.platemap.technique is not None:
        out.append("")
        technique = v.platemap.technique
        if not v.labware:
            out.append(f"Labware for the technique ({technique}): nothing to flag.")
        else:
            n = len(v.labware)
            out.append(
                f"Labware for the technique ({technique}): {n} finding{'s' if n > 1 else ''}."
            )
            for number, finding in enumerate(v.labware, 1):
                out += finding_lines(number, finding, v.source_lines)

    out += ["", "Where every liquid ended up (ul):"]
    out.append(
        f"  {'liquid':<34}{'declared':>9}{'delivered':>10}{'in source':>10}"
        f"{'elsewhere':>10}{'lost':>8}"
    )
    for liquid in v.accounting.liquids:
        elsewhere = sum(volume for _, volume in liquid.elsewhere)
        mark = "  <-- FLAG" if liquid.flags else ""
        out.append(
            f"  {liquid.name[:33]:<34}{liquid.declared_ul:>9.1f}{liquid.delivered_ul:>10.1f}"
            f"{liquid.left_in_source_ul:>10.1f}{elsewhere:>10.1f}{liquid.lost_ul:>8.1f}{mark}"
        )
    for liquid in v.accounting.liquids:
        out += [f"  FLAG: {flag}" for flag in liquid.flags]
    for liquid in v.accounting.liquids:
        out += [f"  Note: {note}" for note in liquid.notes]

    out += ["", "Prep sheet: what to put on the deck before the run."]
    out.append(
        f"  {'slot':<5}{'labware':<38}{'well':<6}{'liquid':<28}{'load at least':>14}"
        f"{'declared':>10}"
    )
    for line in v.prep.lines:
        mark = {None: "", "would_run_dry": "  <-- WOULD RUN DRY", "no_margin": "  <-- NO MARGIN",
                "draws_air": "  <-- DRAWS AIR"}[line.flag]  # fmt: skip
        declared = f"{line.declared_ul:.1f}" if line.declared_ul is not None else "-"
        if line.already_in_plate:
            mark = f"  {already_in_plate_words(line)}"
        out.append(
            f"  {line.slot:<5}{line.labware[:37]:<38}{line.well.well:<6}{line.liquid[:27]:<28}"
            f"{line.needed_ul:>14.1f}{declared:>10}{mark}"
        )
    for line in v.prep.flagged:
        where = f"{line.liquid or 'well'} in {line.well.well}, slot {line.slot}"
        if line.flag == "would_run_dry":
            out.append(
                f"  FLAG: {where} would run dry: the robot draws {_ul(line.needed_ul)} from it and "
                f"the protocol declares {_ul(line.declared_ul or 0)}. The simulator passes it; "
                f"the robot would pipette air. Fix: declare and load at least "
                f"{_ul(max(line.needed_ul * 1.1, line.needed_ul + 50.0))} in this well, or draw "
                "less."
            )
        elif line.flag == "no_margin":
            at_least = max(line.needed_ul * 1.1, line.needed_ul + 50.0)
            out.append(
                f"  FLAG: {where} has no margin: the robot draws {_ul(line.needed_ul)} of the "
                f"{_ul(line.declared_ul or 0)} declared, and a pipette cannot empty a tube to the "
                f"last drop. Fix: in load_liquid for this well, declare at least {_ul(at_least)} "
                f"(10% or 50 ul more than is drawn, whichever is larger), and load that much."
            )
        else:
            out.append(
                f"  FLAG: {where} is asked for {_ul(line.needed_ul)} more than the robot had put "
                "into it at that point, so the pipette draws air."
            )
    for need in v.prep.tips:
        out.append(f"  Tips: {need.tips} from {need.rack} in slot {need.slot}.")
    out.append(
        "  'Load at least' is what the robot draws. Add the dead volume of your tube or reservoir."
    )
    if any(line.already_in_plate for line in v.prep.lines):
        out.append(
            "  A well 'already in the plate' is declared to hold liquid before the run and the "
            "robot only adds to it: put in what is declared."
        )
    out += [
        "",
        "This checks the logic of the protocol: what goes where, and how much. It does not check "
        "the physics: whether a viscous liquid is pipetted accurately, or a drop stays on a tip.",
    ]
    for unknown in v.unplaced:
        out += ["", unknown.sentence]
    return "\n".join(_wrap(line) for line in out) + "\n"


def already_in_plate_words(line: PrepLine) -> str:
    """The words for a declared well the robot only dispenses into, in the text and on the page."""
    return f"already in the plate: {_ul(line.declared_ul or 0)} declared, nothing drawn"


def _wrap(line: str) -> str:
    if len(line) <= WIDTH or line.startswith("  ") and "  " in line.strip():
        return line
    if "http" in line or line.lstrip().startswith("line "):
        return line  # a finding's source link, or the quoted protocol line
    indent = " " * (len(line) - len(line.lstrip()) + 2)
    return textwrap.fill(line, WIDTH, subsequent_indent=indent)


def report_json(v: Verification) -> dict[str, Any]:
    intent = v.intent
    return {
        "protocol": v.protocol_name,
        "platemap": v.platemap.id,
        "technique": v.platemap.technique,
        "exit_code": v.exit_code,
        "labware": [finding.to_json() for finding in v.labware],
        # declared liquids no word list knows: the product asks the student what they are
        "unplaced_liquids": [u.to_json() for u in v.unplaced],
        "intent": {
            "status": intent.status,
            "destination": intent.destination,
            "variant": intent.variant,
            "problems": list(intent.problems),
            "notes": list(intent.notes),
            "wells_ok": sum(r.ok for r in intent.wells),
            "wells_total": len(intent.wells),
            # every checked well, verified or not, so a page can draw the whole plate
            "wells": [_well_json(r) for r in intent.wells],
            "mismatches": [
                {
                    "well": r.well,
                    "group": r.group,
                    "expected": dict(r.expected),
                    "found": dict(r.found),
                    "issues": [
                        {
                            "kind": i.kind,
                            "liquid": i.liquid,
                            "expected_ul": i.expected_ul,
                            "found_ul": i.found_ul,
                            "detail": i.detail,
                        }
                        for i in r.issues
                    ],  # fmt: skip
                }
                for r in intent.mismatches
            ],
        },
        "accounting": [
            {
                "liquid": a.name,
                "logical": a.logical,
                "role": a.role,
                "declared_ul": round(a.declared_ul, 4),
                "delivered_ul": round(a.delivered_ul, 4),
                "left_in_source_ul": round(a.left_in_source_ul, 4),
                "elsewhere": [{"well": str(k), "ul": round(u, 4)} for k, u in a.elsewhere],
                "trash_ul": round(a.trash_ul, 4),
                "lost_ul": round(a.lost_ul, 4),
                "flags": list(a.flags),
                "notes": list(a.notes),
            }
            for a in v.accounting.liquids
        ],
        "prep": prep_json(v.prep),
    }


def prep_json(prep: PrepSheet) -> dict[str, Any]:
    """The prep sheet as JSON: the same shape under `verify.prep` and, for a check with no
    plate map, under the analysis's own `prep` (api.worker), because the sheet needs only
    the trace and the run."""
    return {
        "lines": [
            {
                "slot": p.slot,
                "labware": p.labware,
                "well": p.well.well,
                "liquid": p.liquid,
                "declared_ul": p.declared_ul,
                "needed_ul": round(p.needed_ul, 4),
                "flag": p.flag,
                # declared and never drawn down: the page says so instead of "load 0"
                "already_in_plate": p.already_in_plate,
            }
            for p in prep.lines
        ],  # fmt: skip
        "tips": [{"slot": t.slot, "rack": t.rack, "tips": t.tips} for t in prep.tips],
    }


def _well_json(r: Any) -> dict[str, Any]:
    return {
        "well": r.well,
        "group": r.group,
        "expected": dict(r.expected),
        "found": dict(r.found),
        "ok": r.ok,
        "issues": [
            {
                "kind": i.kind,
                "liquid": i.liquid,
                "expected_ul": i.expected_ul,
                "found_ul": i.found_ul,
                "detail": i.detail,
            }
            for i in r.issues
        ],
    }
