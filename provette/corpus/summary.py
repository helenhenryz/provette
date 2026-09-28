"""Counts from a results file written by `run_corpus`, and a plain-text table of them."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

# Why a library protocol fails on opentrons 8.8.2, in the buckets of the first survey.
# First match wins; each test sees "<error class>: <first line of the message>" in lower case.
_REASONS: list[tuple[str, tuple[str, ...]]] = [
    ("timeout", ("timeout:",)),
    # Not a fault of the protocol: opentrons 8.8.2 builds a module's file name by formatting an
    # enum, and Python 3.11 changed what that gives. Measured: 393 protocols on 3.12, 0 on 3.10.
    ("module lookup broken by Python 3.11+", ("nosuchmoduleerror",)),
    ("PipetteTipType KeyError", ("pipettetiptype",)),
    ("labware too tall", ("labwareheighterror", "too tall", "too high")),
    ("apiLevel too low", ("apiversionerror", "api version", "apilevel")),
    (
        "custom labware missing",
        ("filenotfounderror", "unable to find a labware", "labware definition", "no such file"),
    ),
    (
        "private or removed API internals",
        ("attributeerror", "importerror", "modulenotfounderror", "has no attribute"),
    ),
]


def failure_reason(error_class: str | None, error_message: str | None) -> str:
    text = f"{error_class}: {error_message}".lower()
    for reason, needles in _REASONS:
        if any(needle in text for needle in needles):
            return reason
    return "other"


def _rows(out_path: Path) -> list[dict[str, Any]]:
    with out_path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _api_key(level: str) -> tuple[int, ...]:
    return tuple(int(part) for part in level.split(".") if part.isdigit())


def summarise(out_path: Path) -> dict[str, Any]:
    """Counts by status, failures by reason, and ok/total by category and by apiLevel.

    A protocol in two categories counts in both, so the category totals add to more than the
    number of protocols.
    """
    rows = _rows(out_path)
    failures: dict[str, list[str]] = {}
    by_category: dict[str, Counter[str]] = {}
    by_api: dict[str, Counter[str]] = {}
    for row in rows:
        status = row["status"]
        if status != "ok":
            reason = failure_reason(row.get("error_class"), row.get("error_message"))
            failures.setdefault(reason, []).append(row["slug"])
        for category in row.get("categories") or ["(none)"]:
            by_category.setdefault(category, Counter())[status] += 1
        by_api.setdefault(row.get("api_level") or "(none)", Counter())[status] += 1

    def table(groups: dict[str, Counter[str]]) -> dict[str, dict[str, int]]:
        return {k: {"ok": c["ok"], "total": sum(c.values())} for k, c in groups.items()}

    return {
        "file": str(out_path),
        "total": len(rows),
        "by_status": dict(Counter(row["status"] for row in rows)),
        "seconds_of_work": round(sum(row["seconds"] for row in rows), 1),
        "failures": {k: sorted(v) for k, v in sorted(failures.items(), key=lambda kv: -len(kv[1]))},
        "by_category": dict(sorted(table(by_category).items(), key=lambda kv: -kv[1]["total"])),
        "by_api_level": dict(sorted(table(by_api).items(), key=lambda kv: _api_key(kv[0]))),
    }


def render(summary: dict[str, Any]) -> str:
    total = summary["total"]
    lines = [f"{summary['file']}: {total} protocols"]
    for status in ("ok", "error", "timeout"):
        count = summary["by_status"].get(status, 0)
        share = f"{100 * count / total:5.1f}%" if total else ""
        lines.append(f"  {status:<8}{count:>5} {share}")

    lines += ["", "why they failed"]
    for reason, slugs in summary["failures"].items():
        lines.append(f"  {len(slugs):>4}  {reason}")

    for title, key in (("by category", "by_category"), ("by apiLevel", "by_api_level")):
        lines += ["", f"{title:<44}{'ok':>5}{'of':>6}"]
        for name, counts in summary[key].items():
            lines.append(f"  {name[:40]:<42}{counts['ok']:>5}{counts['total']:>6}")
    return "\n".join(lines)
