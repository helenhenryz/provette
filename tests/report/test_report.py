"""The two reports and the `provette check` command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provette.check import check
from provette.cli import main
from provette.report.json import report_json
from provette.report.text import WIDTH, report_text
from provette.rules import SCHEMA_VERSION

PROTOCOLS = Path(__file__).parent.parent / "fixtures" / "protocols"

FINDING_KEYS = {
    "rule_id",
    "family",
    "tier",
    "severity",
    "certain",
    "roles_basis",
    "title",
    "explanation",
    "fix",
    "line",
    "stack",
    "occurrences",
    "wells",
    "downstream",
    "sources",
    "fingerprint",
}


@pytest.fixture(scope="module")
def buggy_text() -> str:
    return report_text(check(PROTOCOLS / "pcr_buggy.py"))


@pytest.mark.sim
def test_text_report_of_the_buggy_pcr(buggy_text: str) -> None:
    lines = buggy_text.splitlines()
    # the notes: NO-NEGATIVE-CONTROL (the plate has no no-template well) and the proposed
    # declared rule NO-SAMPLE-INTO-REAGENT-WELL, a note because it is proposed, on the same
    # touch as the master-mix error
    assert lines[0] == "pcr_buggy.py: 4 biology problems (2 errors, 2 notes)."
    assert "2. ERROR CONTAM-STOCK: A used tip went into a stock: PCR master mix" in buggy_text
    assert '   line 32:  p300.aspirate(40, rack["A1"])' in lines  # the offending line, quoted
    assert "   Affected: tube A1 in slot 2." in lines
    assert "   Also reached 7 other wells: wells A2, A3, A4, A5, A6, A7 and A8 in slot 1." in lines
    assert any(line.startswith("   Fix: Pick up a fresh tip") for line in lines)
    assert any("labmanager.com" in line for line in lines)
    assert "The Opentrons simulator (8.8.2) passed this protocol" in buggy_text
    assert "\x1b" not in buggy_text  # no colour codes
    assert all(len(line) <= WIDTH or "http" in line for line in lines)


@pytest.mark.sim
def test_text_report_of_the_clean_pcr() -> None:
    text = report_text(check(PROTOCOLS / "pcr_clean.py"))
    # clean of contamination; the one note is the missing no-template control (MIQE)
    assert text.startswith("pcr_clean.py: 1 biology problem (1 note).\n")
    assert "1. NOTE NO-NEGATIVE-CONTROL: No no-template control" in text
    assert "passed this protocol" in text


@pytest.mark.sim
def test_json_report_has_a_stable_shape() -> None:
    report = report_json(check(PROTOCOLS / "pcr_buggy.py"))
    report = json.loads(json.dumps(report))  # it really is JSON
    assert report["schema_version"] == SCHEMA_VERSION == 1
    assert report["protocol"] == "pcr_buggy.py"
    assert report["simulator"] == {"passed": True, "opentrons_version": "8.8.2"}
    assert report["counts"] == {
        "by_severity": {"error": 2, "note": 2},
        "by_rule": {"CONTAM-STOCK": 2, "NO-SAMPLE-INTO-REAGENT-WELL": 1, "NO-NEGATIVE-CONTROL": 1},
    }
    assert {rule["rule_id"] for rule in report["rules"]} >= {"CONTAM-STOCK", "MIX-BEFORE-DRAW"}
    first = report["findings"][1]  # the master mix, line 32
    assert set(first) == FINDING_KEYS
    assert first["occurrences"][0] == {"event_index": 3, "line": 32}
    assert first["wells"][0] == {
        "labware_id": "2:opentrons_24_tuberack_nest_1.5ml_snapcap",
        "well": "A1",
        "slot": "2",
        "labware": "Opentrons 24 Tube Rack with NEST 1.5 mL Snapcap",
        "liquid": "PCR master mix",
    }
    assert first["downstream"]["count"] == 7 == len(first["downstream"]["wells"])
    assert set(first["sources"][0]) == {"name", "url"}
    assert first["roles_basis"] == "inferred"  # the liquids are declared


@pytest.mark.sim
@pytest.mark.parametrize(
    ("name", "code"), [("pcr_clean.py", 0), ("pcr_buggy.py", 1), ("bad_protocol.py", 2)]
)
def test_exit_codes(name: str, code: int, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", str(PROTOCOLS / name)]) == code
    out = capsys.readouterr().out
    if code == 2:
        assert "The Opentrons simulator rejected bad_protocol.py (line 15):" in out
        assert "Cannot aspirate 500.0" in out


@pytest.mark.sim
def test_json_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", str(PROTOCOLS / "pcr_buggy.py"), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["schema_version"] == 1
    assert main(["check", str(PROTOCOLS / "bad_protocol.py"), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["simulator"]["line"] == 15
