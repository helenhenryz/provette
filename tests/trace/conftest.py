"""Shared helpers: each fixture protocol is traced and analysed at most once per test process."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from provette.model import Event, Trace
from provette.trace import LiquidOp, analyze_protocol, trace_protocol

PROTOCOLS = Path(__file__).parent.parent / "fixtures" / "protocols"

# Every fixture the simulator accepts. `cross_check` must be empty for each (plan, layer 2).
GOOD = [
    "pcr_buggy",
    "pcr_clean",
    "multi_channel",
    "partial_tips",
    "transfer_family",
    "modules",
    "helpers_loops",
    "legacy_api",
    "move_labware",
    "trash_and_adapter",
    "refilled_racks",
    "odd_volumes",
    "multi_tube_rack",
]


@cache
def traced(name: str) -> Trace:
    return trace_protocol(PROTOCOLS / f"{name}.py")


@cache
def analyzed(name: str) -> tuple[LiquidOp, ...]:
    return tuple(analyze_protocol(PROTOCOLS / f"{name}.py"))


def brief(event: Event) -> tuple[object, ...]:
    """(op, line, parent, volume, wells, tips) with wells and tips as "A1,B1" strings."""
    wells = ",".join(t.well.well for t in event.targets)
    tips = ",".join(t.tip.well if t.tip else "-" for t in event.targets)
    return (event.op, event.line, event.parent, event.volume_ul, wells, tips)


def liquid(trace: Trace) -> list[Event]:
    """The trace without the "other" events (TRANSFER, MIX... announcements)."""
    return [e for e in trace.events if e.op != "other"]
