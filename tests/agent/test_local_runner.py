"""The local runner keeps the Runner contract on a clean, a buggy and a rejected protocol."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provette.agent.local_runner import LocalRunner

ROOT = Path(__file__).parents[2]
PROTOCOLS = ROOT / "tests" / "fixtures" / "protocols"
PLATEMAP = json.loads((ROOT / "eval" / "platemaps" / "pcr-01.json").read_text())

pytestmark = pytest.mark.sim

CONTRACT_KEYS = {
    "simulator", "simulator_error", "verify_exit", "verify_text", "verify", "check_exit",
    "check_text", "findings", "seconds",
}  # fmt: skip


def test_buggy_protocol_passes_the_simulator_and_fails_both_checks() -> None:
    result = LocalRunner().run_checks((PROTOCOLS / "pcr_buggy.py").read_text(), PLATEMAP)
    assert set(result) == CONTRACT_KEYS
    assert result["simulator"] == "passed" and result["simulator_error"] == ""
    assert result["verify_exit"] == 1 and result["check_exit"] == 1
    assert result["verify"]["intent"]["status"] == "mismatch"
    finding = next(f for f in result["findings"] if f["rule_id"] == "CONTAM-STOCK")
    assert set(finding) == {"rule_id", "severity", "certain", "line", "title", "explanation", "fix"}
    assert finding["severity"] == "error" and finding["line"] in (30, 32)  # the master-mix draw


def test_rejected_protocol_reports_the_error_and_no_check_fields() -> None:
    text = 'metadata = {"apiLevel": "2.19"}\n\n\ndef run(protocol):\n    protocol.nope()\n'
    result = LocalRunner().run_checks(text, PLATEMAP)
    assert result["simulator"] == "rejected" and result["verify_exit"] == 2
    assert "check_exit" not in result and "findings" not in result
    assert result["simulator_error"].startswith("line 5: ") and "nope" in result["simulator_error"]
    assert json.dumps(result)  # serialisable


def test_a_check_that_times_out_comes_back_as_a_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    from provette.agent import local_runner

    monkeypatch.setattr(local_runner, "TIMEOUT_S", 0.001)
    text = (PROTOCOLS / "pcr_clean.py").read_text()
    result = LocalRunner().run_checks(text, {})
    assert result["simulator"] == "rejected" and result["verify_exit"] == 2
    assert "could not finish checking this draft" in result["simulator_error"]
