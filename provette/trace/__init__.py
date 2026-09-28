"""Run an Opentrons protocol under the simulator and get a `provette.model.Trace`.

See README.md in this directory for what may be relied on.
"""

from provette.trace._run import SimulatorTimeout, TraceError, trace_protocol
from provette.trace.analyze import LiquidOp, analyze_protocol
from provette.trace.crosscheck import cross_check

__all__ = [
    "LiquidOp",
    "SimulatorTimeout",
    "TraceError",
    "analyze_protocol",
    "cross_check",
    "trace_protocol",
]
