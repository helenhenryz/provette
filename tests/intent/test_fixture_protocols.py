"""The five fixture protocols through the real simulator, and the command's exit codes."""

from __future__ import annotations

from pathlib import Path

import pytest

from provette.cli import main
from provette.intent import load_platemap
from provette.intent.cli import verify

FIXTURES = Path(__file__).parents[1] / "fixtures" / "intent"
PLATEMAP = FIXTURES / "pcr4.json"


@pytest.mark.sim
@pytest.mark.parametrize(
    ("name", "intent", "accounting_flags", "prep_flags", "exit_code"),
    [
        ("correct", "verified", 0, 0, 0),
        ("wrong_volume", "mismatch", 0, 0, 1),
        ("swapped", "mismatch", 2, 0, 1),
        ("sample_to_trash", "mismatch", 1, 0, 1),
        ("runs_dry", "mismatch", 0, 1, 1),
    ],
)
def test_fixture(
    name: str, intent: str, accounting_flags: int, prep_flags: int, exit_code: int
) -> None:
    result = verify(FIXTURES / f"{name}.py", load_platemap(PLATEMAP))
    assert result.intent.status == intent
    assert len(result.accounting.flagged) == accounting_flags
    assert len(result.prep.flagged) == prep_flags
    assert result.exit_code == exit_code


@pytest.mark.sim
def test_the_command(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["verify", str(FIXTURES / "correct.py"), "--platemap", str(PLATEMAP)]) == 0
    assert "VERIFIED" in capsys.readouterr().out
    other = tmp_path / "other.json"
    other.write_text(PLATEMAP.read_text().replace("master\\\\s*mix", "SYBR"))
    assert main(["verify", str(FIXTURES / "correct.py"), "--platemap", str(other)]) == 3
    assert "CANNOT CHECK" in capsys.readouterr().out
    bad = Path(__file__).parents[1] / "fixtures" / "protocols" / "bad_protocol.py"
    assert main(["verify", str(bad), "--platemap", str(PLATEMAP)]) == 2


@pytest.mark.sim
def test_json_lists_every_checked_well() -> None:
    from provette.intent.report import report_json

    data = report_json(verify(FIXTURES / "correct.py", load_platemap(PLATEMAP)))["intent"]
    assert data["wells_total"] == len(data["wells"]) > 0
    assert all(w["ok"] and w["issues"] == [] for w in data["wells"])
    assert data["mismatches"] == []

    data = report_json(verify(FIXTURES / "wrong_volume.py", load_platemap(PLATEMAP)))["intent"]
    assert [w for w in data["wells"] if not w["ok"]] == data["mismatches"] or all(
        m["well"] in {w["well"] for w in data["wells"] if not w["ok"]} for m in data["mismatches"]
    )
