"""One analysis of one protocol, in a subprocess: the simulator, the biology rules, the plate-map
check and the replay export, from one simulator run.

    python -m api.worker analyse protocol.py [--platemap map.json] > analysis.json
    python -m api.worker preview protocol.py --rule rule.json > findings.json

The API never runs the simulator in its own process: a draft is untrusted code and the simulator
is slow to import, so each analysis is a subprocess with a timeout (`api/analysis.py`). The
result is the pipeline's own JSON, unchanged: `provette check --json` under `check`,
`provette verify --json` under `verify`, and `provette view`'s export under `replay`. What
comes out for a rejected protocol is the same shape the two commands print then:
`simulator.error` and `simulator.line`.
`prep` is the prep sheet (what to load, and what would run dry) for every protocol the
simulator passes: it needs the trace and the run only, so a check with no plate map has it too.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from provette.check import check
from provette.intent.cli import verify_trace
from provette.intent.prep import prep_sheet
from provette.intent.report import prep_json
from provette.intent.report import report_json as verify_json
from provette.intent.report import report_text as verify_text
from provette.intent.spec import PlateMapError, load_platemap
from provette.report.json import report_json as check_json
from provette.report.text import report_text as check_text
from provette.trace import SimulatorTimeout, TraceError
from provette.view.export import export

# An analysis is made once and kept (api/analysis.py), so it may take longer than a live check:
# the heaviest example in the gallery (nano-best3/short-on-tips/fill-01) needs 77 s on a laptop.
SIMULATOR_S = 300.0


def analyse(protocol: Path, platemap: Path | None) -> dict[str, Any]:
    started = time.time()
    out: dict[str, Any] = {
        "protocol": protocol.name,
        "simulator": {"passed": False, "error": None, "line": None},
        "check": None,
        "check_text": None,
        "verify": None,
        "verify_text": None,
        "replay": None,
        "prep": None,
        "platemap_error": None,
    }
    spec = None
    if platemap is not None:
        try:
            spec = load_platemap(platemap)
        except (OSError, PlateMapError) as error:
            out["platemap_error"] = str(error)
    try:
        result = check(protocol, timeout_s=SIMULATOR_S)
    except SimulatorTimeout:
        # no verdict: the worker fails, so api/analysis.py raises AnalysisError, the page says to
        # try again, and nothing is cached (a cached timeout would read as a rejection for ever)
        raise
    except TraceError as error:
        out["simulator"] = {"passed": False, "error": str(error), "line": error.line}
        out["seconds"] = round(time.time() - started, 2)
        return out
    out["simulator"] = {"passed": True, "error": None, "line": None}
    out["check"] = check_json(result)
    out["check_text"] = check_text(result)
    out["prep"] = prep_json(prep_sheet(result.trace, result.run))
    verification = None
    if spec is not None:
        verification = verify_trace(result.trace, result.run, spec)
        out["verify"] = verify_json(verification)
        out["verify_text"] = verify_text(verification)
    out["replay"] = export(result, verification)
    out["seconds"] = round(time.time() - started, 2)
    return out


def main(argv: list[str] | None = None) -> int:
    roles_file = os.environ.get("PROVETTE_ROLES_FILE")
    if roles_file:  # the word lists live elsewhere (a test's copy): read them from there
        from provette.rules import roles

        roles.ROLES_FILE = Path(roles_file)
        roles.reload(Path(roles_file))
    parser = argparse.ArgumentParser(prog="python -m api.worker")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyse")
    p.add_argument("protocol", type=Path)
    p.add_argument("--platemap", type=Path)
    q = sub.add_parser("preview")
    q.add_argument("protocol", type=Path)
    q.add_argument("--rule", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "preview":
        json.dump(preview(args.protocol, args.rule), sys.stdout, separators=(",", ":"))
        return 0
    json.dump(analyse(args.protocol, args.platemap), sys.stdout, separators=(",", ":"))
    return 0


def preview(protocol: Path, rule_path: Path) -> dict[str, Any]:
    """One declared rule (a JSON file of its fields) on one protocol: `declared.preview`."""
    from provette.rules import declared

    rule = json.loads(rule_path.read_text(encoding="utf-8"))
    started = time.time()
    try:
        findings = declared.preview(rule, protocol)
    except SimulatorTimeout:
        raise
    except TraceError as error:
        return {
            "simulator": {"passed": False, "error": str(error), "line": error.line},
            "findings": [],
            "seconds": round(time.time() - started, 2),
        }
    return {
        "simulator": {"passed": True, "error": None, "line": None},
        "findings": [f.to_json() for f in findings],
        "seconds": round(time.time() - started, 2),
    }


if __name__ == "__main__":
    sys.exit(main())
