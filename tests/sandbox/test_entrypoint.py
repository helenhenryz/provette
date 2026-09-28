"""The entrypoint in-process, on the fixture protocols: the contract's dict, whatever happens."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from provette.sandbox import entrypoint

from .conftest import PLATEMAPS, PROTOCOLS

CONTRACT_KEYS = {"simulator", "simulator_error", "verify_exit", "verify_text", "verify", "seconds"}
PASSED_KEYS = CONTRACT_KEYS | {"check_exit", "check_text", "findings"}


def work_dir(tmp_path: Path, protocol: str, platemap: str) -> Path:
    shutil.copy(PROTOCOLS / protocol, tmp_path / entrypoint.PROTOCOL)
    shutil.copy(PLATEMAPS / platemap, tmp_path / entrypoint.PLATEMAP)
    return tmp_path


@pytest.mark.sim
def test_buggy_protocol_is_a_mismatch_with_findings(tmp_path: Path) -> None:
    result = entrypoint.run_work_dir(work_dir(tmp_path, "pcr_buggy.py", "pcr-01.json"))
    assert set(result) == PASSED_KEYS
    assert result["simulator"] == "passed" and result["simulator_error"] == ""
    assert result["verify_exit"] in (1, 3) and result["check_exit"] == 1
    assert result["verify"]["protocol"] == entrypoint.PROTOCOL
    assert result["findings"], "pcr_buggy carries rule findings"
    assert set(result["findings"][0]) == set(entrypoint.FINDING_KEYS)
    assert result["seconds"] > 0
    written = json.loads((tmp_path / entrypoint.RESULT).read_text(encoding="utf-8"))
    assert written == result


@pytest.mark.sim
def test_rejected_protocol_has_no_check_fields(tmp_path: Path) -> None:
    result = entrypoint.run_work_dir(work_dir(tmp_path, "bad_protocol.py", "pcr-01.json"))
    assert set(result) == CONTRACT_KEYS
    assert result["simulator"] == "rejected" and result["verify_exit"] == 2
    assert result["simulator_error"] and result["simulator_error"] == result["verify_text"]


@pytest.mark.sim
def test_main_prints_the_result(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    work = work_dir(tmp_path, "pcr_clean.py", "pcr-01.json")
    assert entrypoint.main(["--work", str(work), "--print"]) == 0
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["simulator"] == "passed"
    assert printed == json.loads((work / entrypoint.RESULT).read_text(encoding="utf-8"))


def test_unreadable_platemap_is_reported_not_raised(tmp_path: Path) -> None:
    (tmp_path / entrypoint.PROTOCOL).write_text("metadata = {}\n", encoding="utf-8")
    (tmp_path / entrypoint.PLATEMAP).write_text("not json", encoding="utf-8")
    result = entrypoint.run_work_dir(tmp_path)
    assert result["verify_exit"] == 3 and result["simulator"] == "passed"
    assert "Cannot read the plate map" in result["verify_text"]
