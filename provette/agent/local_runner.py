"""`LocalRunner`: the checks run on this machine, as subprocesses, in a temporary directory.

What eval/baseline/run.py's `judge` did, behind the `Runner` contract: the draft and the plate map
are written to a temp dir, then `python -m provette.cli verify --json`, `verify` (text), `check`
and `check --json` run there with the same interpreter. OT_API_CONFIG_DIR points into the temp
dir so the simulator writes nothing anywhere else, and PYTHONPATH is unset (a machine with ROS
sourced breaks the simulator otherwise). The draft runs with this machine's privileges: this is
the development runner. The sandbox runner (`provette.sandbox`) is the one for untrusted drafts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TIMEOUT_S = 600
TIMEOUT_MESSAGE = (
    f"Provette could not finish checking this draft in {TIMEOUT_S} s. It replays every step of "
    "the protocol, and this one has too many for that. Write it with fewer, larger steps: "
    "transfer lists instead of one call per well, and the multichannel pipette where the "
    "request allows."
)


class LocalRunner:
    name = "local"

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        started = time.time()
        with tempfile.TemporaryDirectory(prefix="provette-agent-") as tmp:
            work = Path(tmp)
            protocol = work / "protocol.py"
            platemap = work / "platemap.json"
            protocol.write_text(protocol_text, encoding="utf-8")
            platemap.write_text(json.dumps(platemap_json), encoding="utf-8")
            (work / "opentrons-config").mkdir()
            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["OT_API_CONFIG_DIR"] = str(work / "opentrons-config")

            def provette(*args: str) -> tuple[int, str]:
                try:
                    done = subprocess.run(
                        [sys.executable, "-m", "provette.cli", *args],
                        cwd=work,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_S,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    # Reported to the model like a simulator rejection, so the episode goes
                    # on: a draft the replay cannot finish in time is a draft to rewrite.
                    return 2, json.dumps({"simulator": {"error": TIMEOUT_MESSAGE, "line": None}})
                return done.returncode, (done.stdout + done.stderr).strip()

            verify_exit, verify_json_text = provette(
                "verify", "protocol.py", "--platemap", "platemap.json", "--json"
            )
            verify_json = _json(verify_json_text)
            if verify_exit == 2:
                rejected = verify_json.get("simulator", {})
                line = rejected.get("line")
                message = rejected.get("error") or (
                    "the verifier gave no readable result; its output was:\n" + verify_json_text
                )
                return {
                    "simulator": "rejected",
                    "simulator_error": (f"line {line}: " if line is not None else "") + message,
                    "verify_exit": 2,
                    "verify_text": verify_json_text,
                    "verify": verify_json,
                    "seconds": round(time.time() - started, 1),
                }
            _, verify_text = provette("verify", "protocol.py", "--platemap", "platemap.json")
            check_exit, check_text = provette("check", "protocol.py")
            _, check_json_text = provette("check", "protocol.py", "--json")
            findings = _json(check_json_text).get("findings", [])
            return {
                "simulator": "passed",
                "simulator_error": "",
                "verify_exit": verify_exit,
                "verify_text": verify_text,
                "verify": verify_json,
                "check_exit": check_exit,
                "check_text": check_text,
                "findings": [
                    {
                        k: f.get(k)
                        for k in (
                            "rule_id",
                            "severity",
                            "certain",
                            "line",
                            "title",
                            "explanation",
                            "fix",
                        )
                    }
                    for f in findings
                ],
                "seconds": round(time.time() - started, 1),
            }

    def close(self) -> None:
        """Nothing is held between calls."""


def _json(text: str) -> dict[str, Any]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}
