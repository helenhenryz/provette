"""Step 3: plant bugs in the plain-condition protocols that verify clean; see who catches them.

    env -u PYTHONPATH uv run python eval/checks/run_mutants.py

Writes results/mutants.json: one row per mutant, with the diff against the original, whether
the simulator still passes it, and what each check said.
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from mutate import HELPER, mutants  # noqa: E402

from provette.intent.cli import verify_trace  # noqa: E402
from provette.intent.report import Verification  # noqa: E402
from provette.intent.spec import load_platemap  # noqa: E402
from provette.rules import run_rules  # noqa: E402
from provette.state import Run, replay  # noqa: E402
from provette.trace import TraceError, trace_protocol  # noqa: E402

# FIRST_TOLERANCE=1 reruns everything with the tolerance the experiment started with (the larger
# of 2% and 0.2 ul), to show what the change to `tolerance_ul` bought. Results go to a second file.
FIRST = os.environ.get("FIRST_TOLERANCE") == "1"
if FIRST:
    import provette.intent.compare as _compare

    _compare.tolerance_ul = lambda expected_ul: max(0.02 * expected_ul, 0.2)

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
MAPS = ROOT / "eval" / "platemaps"
PLAIN = HERE / "protocols" / "plain"


def deck_by_name(run: Run, only_labware: str | None = None) -> dict[str, dict[str, float]]:
    """Every well's contents by declared liquid NAME, so two runs can be compared."""
    out: dict[str, dict[str, float]] = {}
    for key, state in run.wells.items():
        if only_labware is not None and key.labware_id != only_labware:
            continue
        contents: dict[str, float] = {}
        for atom, presence in state.atoms.items():
            if presence.volume_ul and presence.volume_ul > 1e-6:
                name = run.origins[atom].liquid_name or str(atom)
                contents[name] = round(contents.get(name, 0.0) + presence.volume_ul, 4)
        if contents:
            out[str(key)] = contents
    return out


def check(path: Path, request_id: str) -> tuple[Verification, Run, list[str]]:
    trace = trace_protocol(path)
    run = replay(trace)
    lines = tuple(path.read_text().splitlines())
    findings = [f"{f.severity} {f.rule_id}" for f in run_rules(trace, run, lines)]
    return verify_trace(trace, run, load_platemap(MAPS / f"{request_id}.json")), run, findings


def one(request_id: str) -> list[dict[str, Any]]:
    original_path = PLAIN / f"{request_id}.py"
    source = original_path.read_text()
    base, base_run, base_findings = check(original_path, request_id)
    assert base.exit_code == 0, request_id
    normal = ast.unparse(ast.parse(source)).splitlines()
    helper_lines = set(HELPER.splitlines()) | {""}
    rows = []
    for number, mutant in enumerate(mutants(source)):
        mutated = mutant.source.splitlines()
        row: dict[str, Any] = {
            "id": request_id,
            "mutant": f"{request_id}-{mutant.operator}{number}",
            "operator": mutant.operator,
            "line": mutant.line,
            "description": mutant.description,
            "diff": [
                d for d in difflib.unified_diff(normal, mutated, lineterm="", n=0)
                if not d.startswith(("---", "+++", "@@")) and d[1:] not in helper_lines
            ],
        }  # fmt: skip
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"{request_id}.py"
            path.write_text(mutant.source)
            try:
                result, run, findings = check(path, request_id)
            except TraceError as error:
                rows.append({**row, "simulator": "rejected", "error": str(error)[:200]})
                continue
        destination = base.intent.destination
        bad = result.intent.mismatches
        lost = [a for a in result.accounting.liquids if a.role == "sample" and a.lost_ul > 0.05]
        row.update(
            simulator="passed",
            intent=result.intent.status,
            order_note=any("not in the order" in note for note in result.intent.notes),
            mismatching_wells=len(result.intent.mismatches),
            first_issue=next(
                (f"{r.well}: {i.kind} {i.liquid}" for r in bad for i in r.issues),
                None,
            ),
            accounting_flags=[flag for a in result.accounting.flagged for flag in a.flags],
            sample_lost=bool(lost),
            prep_flags=[f"{p.liquid} {p.well.well} {p.flag}" for p in result.prep.flagged],
            check_findings=[f for f in findings if f not in base_findings],
            same_deck=deck_by_name(run) == deck_by_name(base_run),
            same_destination=deck_by_name(run, destination) == deck_by_name(base_run, destination),
            layout_free=not any(v.pinned for v in result.platemap.variants)
            and all(g.position == "free" and g.within is None
                    for v in result.platemap.variants for g in v.groups),
        )  # fmt: skip
        rows.append(row)
    return rows


def main() -> None:
    ids = sorted(path.stem for path in MAPS.glob("*.json"))
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows = [row for rows in pool.map(one, ids) for row in rows]
    name = "mutants_first_tolerance.json" if FIRST else "mutants.json"
    (HERE / "results" / name).write_text(json.dumps(rows, indent=1) + "\n")
    print(
        len(rows), "mutants;", sum(r["simulator"] == "passed" for r in rows), "pass the simulator"
    )


if __name__ == "__main__":
    main()
