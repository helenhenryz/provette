"""`provette trace`."""

from __future__ import annotations

from pathlib import Path

import pytest

from provette.cli import main
from provette.model import Trace
from tests.trace.conftest import PROTOCOLS

pytestmark = pytest.mark.sim


def test_listing_and_cross_check(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", str(PROTOCOLS / "multi_channel.py"), "--cross-check"]) == 0
    out = capsys.readouterr()
    lines = out.out.splitlines()
    assert len(lines) == 10
    assert "aspirate" in lines[1] and "100 uL" in lines[1] and "A1 x8" in lines[1]
    assert "agree" in out.err


def test_out_writes_a_loadable_trace(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "trace.jsonl"
    assert main(["trace", str(PROTOCOLS / "pcr_buggy.py"), "--out", str(target)]) == 0
    assert capsys.readouterr().out == ""
    assert len(Trace.load(target).events) == 34


def test_a_rejected_protocol_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", str(PROTOCOLS / "bad_protocol.py")]) == 2
    assert "line 15" in capsys.readouterr().err
