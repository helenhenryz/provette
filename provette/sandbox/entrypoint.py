"""What runs inside the sandbox: `provette verify` and `provette check` on one draft, as one JSON.

    python -m provette.sandbox.entrypoint --work /work            # writes /work/result.json
    python -m provette.sandbox.entrypoint --work /work --print    # and prints it to stdout

The folder holds `protocol.py` and `platemap.json`. The result has the shape the runner contract
in `provette/agent/runner.py` promises, and it is computed exactly as `judge` in
`eval/baseline/run.py` does: verify (text and JSON), then, if the simulator passed, check
(text and JSON). The same function runs in-process in the tests, in the Docker image, and in
a Nebius sandbox.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROTOCOL = "protocol.py"
PLATEMAP = "platemap.json"
RESULT = "result.json"

# The keys of a finding the model is shown. `provette check --json` carries more (wells, stack,
# sources); the contract in runner.py names these.
FINDING_KEYS = ("rule_id", "severity", "certain", "line", "title", "explanation", "fix")
TIMED_OUT = 4  # `provette check`/`verify`'s exit when the simulator did not finish in time


def _provette(*args: str, cwd: Path, timeout_s: float) -> tuple[int, str]:
    """`provette <args>` with this interpreter, as `judge` runs it: stdout and stderr joined."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.setdefault("OT_API_CONFIG_DIR", str(cwd / "ot-config"))
    try:
        done = subprocess.run(
            [sys.executable, "-m", "provette.cli", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return TIMED_OUT, f"The Opentrons simulator did not finish within {timeout_s:g} s"
    return done.returncode, (done.stdout + done.stderr).strip()


def _loads(text: str) -> dict[str, Any]:
    """The JSON a subcommand printed, or {} if it printed something else."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def run_checks(protocol: Path, platemap: Path, *, timeout_s: float = 240) -> dict[str, Any]:
    """Every check on one draft. Never raises for a bad protocol: the dict says what happened."""
    started = time.monotonic()
    cwd = protocol.resolve().parent
    verify_exit, verify_text = _provette(
        "verify", str(protocol), "--platemap", str(platemap), cwd=cwd, timeout_s=timeout_s
    )
    if verify_exit == TIMED_OUT:
        # no verdict: the machine was too slow or too busy, not the draft wrong
        return _timed_out(verify_text, started)
    if verify_exit == 2:
        return {
            "simulator": "rejected",
            "simulator_error": verify_text,
            "verify_exit": 2,
            "verify_text": verify_text,
            "verify": {},
            "seconds": round(time.monotonic() - started, 2),
        }
    _, verify_json = _provette(
        "verify", str(protocol), "--platemap", str(platemap), "--json", cwd=cwd, timeout_s=timeout_s
    )
    check_exit, check_text = _provette("check", str(protocol), cwd=cwd, timeout_s=timeout_s)
    if check_exit == TIMED_OUT:
        return _timed_out(check_text, started)
    _, check_json = _provette("check", str(protocol), "--json", cwd=cwd, timeout_s=timeout_s)
    findings = _loads(check_json).get("findings", [])
    if not isinstance(findings, list):
        findings = []
    return {
        "simulator": "passed",
        "simulator_error": "",
        "verify_exit": verify_exit,  # 0 verified, 1 mismatch or flag, 3 cannot check
        "verify_text": verify_text,
        "verify": _loads(verify_json),
        "check_exit": check_exit,  # 0 clean, 1 an error or a warning
        "check_text": check_text,
        "findings": [{k: f.get(k) for k in FINDING_KEYS} for f in findings if isinstance(f, dict)],
        "seconds": round(time.monotonic() - started, 2),
    }


def _timed_out(text: str, started: float) -> dict[str, Any]:
    """The checks did not finish in time: `simulator` is "timeout", never "rejected", so neither
    the agent nor a page reads a slow machine as a verdict on the draft."""
    return {
        "simulator": "timeout",
        "simulator_error": text,
        "verify_exit": TIMED_OUT,
        "verify_text": text,
        "verify": {},
        "seconds": round(time.monotonic() - started, 2),
    }


def run_work_dir(work: Path, *, timeout_s: float = 240) -> dict[str, Any]:
    """`run_checks` on `<work>/protocol.py` and `<work>/platemap.json`, written to `result.json`."""
    result = run_checks(work / PROTOCOL, work / PLATEMAP, timeout_s=timeout_s)
    (work / RESULT).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provette-run-checks", description=__doc__)
    parser.add_argument("--work", type=Path, default=Path("/work"))
    parser.add_argument("--timeout", type=float, default=240, help="seconds per simulator run")
    parser.add_argument("--print", action="store_true", help="also print the result to stdout")
    args = parser.parse_args(argv)
    result = run_work_dir(args.work, timeout_s=args.timeout)
    if args.print:
        sys.stdout.write(json.dumps(result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
