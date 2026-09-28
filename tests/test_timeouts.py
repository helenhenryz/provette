"""A check that runs out of time is never a verdict. A slow or busy machine (a throttled shared CPU,
two runs at once) must not be read as a rejected draft by the model, shown as one on a page, or
cached as one: each layer that sees the simulator run out of time says so, and only that."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import pytest

from api import analysis
from api.steps import checks_sentence
from provette.agent.tools import Toolbox, checks_for_model
from provette.sandbox import entrypoint
from provette.trace import SimulatorTimeout, TraceError
from tests.agent.test_tools import CLEAN, load


def test_a_timeout_is_a_trace_error_of_its_own() -> None:
    assert issubclass(
        SimulatorTimeout, TraceError
    )  # every caller that catches TraceError still does


def test_check_and_verify_exit_4_on_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import provette.check as check_module
    import provette.intent.cli as verify_module

    def slow(*_: Any, **__: Any) -> Any:
        raise SimulatorTimeout("the simulator did not finish within 1 s")

    monkeypatch.setattr(check_module, "check", slow)
    monkeypatch.setattr(verify_module, "verify", slow)
    monkeypatch.setattr(verify_module, "load_platemap", lambda _p: object())
    args = argparse.Namespace(protocol=Path("p.py"), json=False, labware_dir=None, platemap="m")
    assert check_module._command(args) == check_module.EXIT_TIMEOUT == 4
    assert verify_module._command(args) == verify_module.EXIT_TIMEOUT == 4


def test_the_runner_says_timeout_never_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(entrypoint, "_provette", lambda *a, **k: (4, "did not finish within 1 s"))
    result = entrypoint.run_checks(tmp_path / "protocol.py", tmp_path / "platemap.json")
    assert result["simulator"] == "timeout" and result["verify_exit"] == 4
    assert "rejected" not in result["simulator"]


class SlowThenFast:
    """A runner that times out, then answers: the second call is the retry."""

    name = "slow"

    def __init__(self, *results: dict[str, Any]) -> None:
        self.results = list(results)
        self.calls = 0

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return dict(self.results.pop(0) if len(self.results) > 1 else self.results[0])

    def close(self) -> None:
        pass


TIMEOUT = {"simulator": "timeout", "simulator_error": "did not finish", "verify_exit": 4}


def test_the_agent_retries_a_timed_out_check_once(tmp_path: Path) -> None:
    runner = SlowThenFast(TIMEOUT, CLEAN)
    box = Toolbox(load("pcr-01"), runner, tmp_path)
    shown = box.call("write_protocol", {"text": "x = 1\n"})["checks"]
    assert runner.calls == 2 and shown["ready_to_submit"] is True  # the retry answered


def test_a_timeout_the_retry_cannot_clear_is_told_as_the_servers(tmp_path: Path) -> None:
    runner = SlowThenFast(TIMEOUT)
    box = Toolbox(load("pcr-01"), runner, tmp_path)
    shown = box.call("write_protocol", {"text": "x = 1\n"})["checks"]
    assert runner.calls == 2 and shown["simulator"] == "timeout"
    assert "not a finding about your draft" in shown["verdict"]
    assert "rejected" not in shown["verdict"] and "simulator_error" not in shown
    # sending the same file again is what it was told to do: no "identical draft" scolding
    again = box.call("write_protocol", {"text": "x = 1\n"})
    assert "same_as_previous_draft" not in again
    assert checks_for_model({**TIMEOUT, "draft": 1})["ready_to_submit"] is False


def test_the_run_page_says_the_checks_did_not_finish() -> None:
    title, detail, status = checks_sentence({**TIMEOUT, "draft": 3})
    assert title == "Draft 3: the checks did not finish in time" and status == "info"
    assert "rejected" not in title and "nothing in the draft was judged" in detail


def test_a_timed_out_analysis_is_said_plainly_and_never_cached(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def worker(args: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        stderr = "Traceback ...\nprovette.trace._run.SimulatorTimeout: did not finish within 120 s"
        return subprocess.CompletedProcess(args, 1, stdout="", stderr=stderr)

    monkeypatch.setattr(analysis.subprocess, "run", worker)
    with pytest.raises(analysis.AnalysisError, match="did not finish in time; the server is busy"):
        analysis.analyse("print(1)", None, cache_dir=tmp_path)
    assert not list(tmp_path.glob("*.json"))  # nothing cached: the next visit tries again
