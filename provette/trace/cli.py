"""`provette trace <protocol>`: print what a protocol does, step by step, or save the trace."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from provette.model import Event
from provette.trace import TraceError, analyze_protocol, cross_check, trace_protocol


def register(sub: Any) -> None:
    parser = sub.add_parser("trace", help="run a protocol under the simulator and list its steps")
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--labware-dir", action="append", default=[], type=Path, metavar="D")
    parser.add_argument("--out", type=Path, help="write the trace as JSON Lines instead")
    parser.add_argument(
        "--cross-check",
        action="store_true",
        help="also run `opentrons analyze` and fail if the two disagree",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    try:
        trace = trace_protocol(args.protocol, labware_dirs=args.labware_dir)
        problems = (
            cross_check(trace, analyze_protocol(args.protocol, labware_dirs=args.labware_dir))
            if args.cross_check
            else []
        )
    except TraceError as error:
        where = f" (protocol line {error.line})" if error.line else ""
        print(f"the simulator rejected {args.protocol.name}{where}:\n{error}", file=sys.stderr)
        return 2
    if args.out:
        trace.dump(args.out)
    else:
        for event in trace.events:
            print(format_event(event))
    for problem in problems:
        print(f"cross-check: {problem}", file=sys.stderr)
    if args.cross_check and not problems:
        print("cross-check: the broker trace and the analysis agree", file=sys.stderr)
    return 1 if problems else 0


def format_event(event: Event) -> str:
    """One line per event: index, time, line, op, volume, wells, tip, height, parent."""
    parts = [f"{event.index:4d}", f"{event.t_est_s:8.1f}s", f"L{event.line or '?':<4}"]
    parts.append(f"{event.op:<12}")
    if event.volume_ul is not None:
        parts.append(f"{event.volume_ul:g} uL")
    if event.targets:
        wells = [t.well.well for t in event.targets]
        tips = [t.tip.well if t.tip else "none" for t in event.targets]
        parts.append(f"{event.targets[0].well.labware_id}[{_span(wells)}]")
        if event.op != "pick_up_tip":
            parts.append(f"tip {_span(tips)}")
    if event.height_mm is not None:
        parts.append(f"{event.height_mm:g} mm up")
    if event.returned:
        parts.append("returned to rack")
    if event.celsius is not None:
        parts.append(f"{event.celsius:g} C")
    if event.duration_s is not None:
        parts.append(f"{event.duration_s:g} s")
    if event.module:
        parts.append(f"on {event.module}")
    if event.parent:
        parts.append(f"(in {event.parent})")
    if event.op in ("other", "lid", "pause", "move_labware", "thermocycler_profile"):
        parts.append(f"- {event.detail}")
    return " ".join(parts)


def _span(names: list[str]) -> str:
    if len(set(names)) == 1:
        return names[0] if len(names) == 1 else f"{names[0]} x{len(names)}"
    return ",".join(names)
