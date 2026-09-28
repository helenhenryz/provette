"""`provette verify protocol.py --platemap map.json`: does the protocol make the plate asked for?

Exit codes: 0 every well verified and nothing flagged, 1 a mismatch, a flag or a labware warning,
2 the simulator rejected the protocol, 3 the plate map could not be checked against this
protocol.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from provette.intent.accounting import account
from provette.intent.compare import compare
from provette.intent.labware import labware_for_technique
from provette.intent.prep import prep_sheet
from provette.intent.report import Verification, report_json, report_text
from provette.intent.spec import PlateMap, PlateMapError, load_platemap
from provette.model import Trace
from provette.rules.roles import unplaced
from provette.state import Run, replay
from provette.trace import SimulatorTimeout, TraceError, trace_protocol

# the simulator did not finish in time: no verdict either way (0/1 a verdict, 2 rejected, 3 no map)
EXIT_TIMEOUT = 4


def verify_trace(
    trace: Trace, run: Run, platemap: PlateMap, source_lines: Sequence[str] = ()
) -> Verification:
    """`source_lines`, when given, let the report quote the line a labware finding points at."""
    intent = compare(trace, run, platemap)
    return Verification(
        trace.deck.protocol_name,
        platemap,
        intent,
        account(trace, run, platemap, intent),
        prep_sheet(trace, run),
        tuple(labware_for_technique(trace, platemap, intent, source_lines or None)),
        tuple(source_lines),
        tuple(unplaced(trace)),
    )


def verify(path: Path, platemap: PlateMap, labware_dirs: Sequence[Path] = ()) -> Verification:
    """Raises `provette.trace.TraceError` if the simulator rejects the protocol."""
    trace = trace_protocol(path, labware_dirs=labware_dirs)
    source_lines = tuple(path.read_text(encoding="utf-8", errors="replace").splitlines())
    return verify_trace(trace, replay(trace), platemap, source_lines)


def _command(args: argparse.Namespace) -> int:
    try:
        platemap = load_platemap(args.platemap)
    except (OSError, PlateMapError) as error:
        print(f"Cannot read the plate map {args.platemap}: {error}")
        return 3
    try:
        result = verify(args.protocol, platemap, labware_dirs=args.labware_dir or ())
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
    return result.exit_code


def register(sub: Any) -> None:
    p = sub.add_parser("verify", help="check that a protocol makes the plate a plate map asks for")
    p.add_argument("protocol", type=Path)
    p.add_argument("--platemap", type=Path, required=True, help="the plate map (JSON)")
    p.add_argument("--labware-dir", type=Path, action="append", help="custom labware (*.json)")
    p.add_argument("--json", action="store_true", help="the verification as JSON")
    p.set_defaults(func=_command)
