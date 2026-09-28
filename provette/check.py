"""`provette check protocol.py`: trace it, replay it, run every rule, print the biology bugs.

    result = check(Path("protocol.py"))
    result.findings  # worst first, then in file order

Exit codes of the command: 0 no error or warning, 1 at least one, 2 the simulator rejected
the protocol (its message and line are printed).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from provette.model import Trace
from provette.report.json import report_json
from provette.report.text import report_text
from provette.rules import Finding, run_rules
from provette.state import Run, replay
from provette.trace import SimulatorTimeout, TraceError, trace_protocol


@dataclass(frozen=True)
class CheckResult:
    """The findings, and the trace and the state they came from (the web replay wants both)."""

    path: Path
    source_lines: tuple[str, ...]
    findings: tuple[Finding, ...]
    trace: Trace
    run: Run

    @property
    def failed(self) -> bool:
        """At least one error or warning."""
        return any(finding.severity in ("error", "warning") for finding in self.findings)


# the simulator did not finish in time: no verdict either way (0/1 a verdict, 2 rejected, 3 no map)
EXIT_TIMEOUT = 4


def check(path: Path, labware_dirs: Sequence[Path] = (), timeout_s: float = 120) -> CheckResult:
    """Raises `provette.trace.TraceError` if the simulator rejects the protocol."""
    trace = trace_protocol(path, labware_dirs=labware_dirs, timeout_s=timeout_s)
    run = replay(trace)
    source_lines = tuple(path.read_text(encoding="utf-8", errors="replace").splitlines())
    return CheckResult(path, source_lines, tuple(run_rules(trace, run, source_lines)), trace, run)


def _command(args: argparse.Namespace) -> int:
    try:
        result = check(args.protocol, labware_dirs=args.labware_dir or ())
    except SimulatorTimeout as error:
        if args.json:
            timed: dict[str, Any] = {"error": str(error), "line": None, "timeout": True}
            print(json.dumps({"protocol": args.protocol.name, "simulator": timed}, indent=2))
        else:
            print(f"The checks on {args.protocol.name} did not finish in time:\n  {error}")
        return EXIT_TIMEOUT
    except TraceError as error:
        where = f" (line {error.line})" if error.line is not None else ""
        if args.json:
            rejected: dict[str, Any] = {"error": str(error), "line": error.line}
            print(json.dumps({"protocol": args.protocol.name, "simulator": rejected}, indent=2))
        else:
            print(f"The Opentrons simulator rejected {args.protocol.name}{where}:\n  {error}")
        return 2
    if args.json:
        print(json.dumps(report_json(result), indent=2))
    else:
        sys.stdout.write(report_text(result))
    return 1 if result.failed else 0


def register(sub: Any) -> None:
    p = sub.add_parser("check", help="find the biology bugs in a protocol the simulator passes")
    p.add_argument("protocol", type=Path)
    p.add_argument("--labware-dir", type=Path, action="append", help="custom labware (*.json)")
    p.add_argument("--json", action="store_true", help="the findings as JSON (stable schema)")
    p.set_defaults(func=_command)
