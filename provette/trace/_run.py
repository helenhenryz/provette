"""Running the simulator in a child process, and the one error this module raises."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from provette.model import Trace

ERROR_MARKER = "PROVETTE_TRACE_ERROR "


class TraceError(Exception):
    """The simulator rejected the protocol, or did not finish in time.

    `str(error)` is the simulator's own text. `line` is the protocol line it names, if any.
    """

    def __init__(self, message: str, line: int | None = None) -> None:
        super().__init__(message)
        self.line = line


class SimulatorTimeout(TraceError):
    """The simulator did not finish in time: not a verdict on the protocol. A busy or slow
    machine causes it, so it is never reported as a rejection and never cached as one."""


def run_python(
    arguments: Sequence[str], *, workdir: Path, timeout_s: float
) -> subprocess.CompletedProcess[str]:
    """`python <arguments>` with the same interpreter, writing nothing outside `workdir`."""
    config = workdir / "opentrons-config"
    config.mkdir(exist_ok=True)
    env = {**os.environ, "OT_API_CONFIG_DIR": str(config)}
    try:
        return subprocess.run(
            [sys.executable, *arguments],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise SimulatorTimeout(f"the simulator did not finish within {timeout_s:g} s") from error


def trace_protocol(
    path: Path, *, labware_dirs: Sequence[Path] = (), timeout_s: float = 120
) -> Trace:
    """Run `path` under the Opentrons simulator and return what it did, event by event."""
    path = path.resolve()
    if not path.is_file():
        raise TraceError(f"no such protocol file: {path}")
    with tempfile.TemporaryDirectory(prefix="provette-trace-") as tmp:
        workdir = Path(tmp)
        out = workdir / "trace.jsonl"
        arguments = ["-m", "provette.trace._worker", str(path), str(out)]
        for directory in labware_dirs:
            arguments += ["--labware-dir", str(directory.resolve())]
        done = run_python(arguments, workdir=workdir, timeout_s=timeout_s)
        if done.returncode != 0:
            raise _error_from(done.stderr)
        return Trace.load(out)


def _error_from(stderr: str) -> TraceError:
    for text in reversed(stderr.splitlines()):
        if text.startswith(ERROR_MARKER):
            report = json.loads(text[len(ERROR_MARKER) :])
            return TraceError(report["error"], report["line"])
    return TraceError("the tracer process died:\n" + stderr[-2000:])
