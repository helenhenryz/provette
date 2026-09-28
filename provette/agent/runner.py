"""Where a draft protocol is executed: the contract between the agent loop and the sandbox.

A `Runner` takes the text of a protocol and a plate map, runs the simulator, `provette verify` and
`provette check` on it, and returns everything the model needs as one JSON-serialisable dict. Two
implementations share this contract: a local one (this machine, or a local Docker container)
and a Nebius Token Factory Sandbox. The agent loop does not know which it has.

The dict a runner returns:

    {
      "simulator": "passed" | "rejected",
      "simulator_error": str,            # "" when passed; the message and line when not
      "verify_exit": 0 | 1 | 2 | 3,      # 0 verified, 1 mismatch or flag, 2 rejected, 3 no check
      "verify_text": str,                # the plain-English report a student reads
      "verify": dict,                    # `provette verify --json`
      "check_exit": 0 | 1,               # 0 clean, 1 an error or a warning
      "check_text": str,
      "findings": list[dict],            # rule_id, severity, certain, line, title, explanation, fix
      "seconds": float,
    }

When the simulator rejects the protocol, verify_exit is 2 and the check fields are absent.
"""

from __future__ import annotations

from typing import Any, Protocol


class Runner(Protocol):
    name: str

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        """Run every check on one draft. Never raises for a bad protocol: the dict says."""
        ...

    def close(self) -> None:
        """Release whatever the runner holds (a container, a sandbox instance)."""
        ...
