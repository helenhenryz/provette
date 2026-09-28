"""The fingerprint is what our triage labels are keyed on. It must survive edits that
have nothing to do with the finding, and change when the finding is about other wells."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from provette.check import CheckResult, check
from provette.rules.finding import Downstream, Finding, Occurrence, Source, WellRef, fingerprint
from tests.rules.conftest import PROTOCOLS

BUGGY = PROTOCOLS / "pcr_buggy.py"


def _finding(line: int, stack: tuple[str, ...], wells: tuple[str, ...]) -> Finding:
    return Finding(
        rule_id="CONTAM-STOCK",
        family=1,
        tier="structural",
        severity="error",
        certain=True,
        roles_basis="none",
        title="t",
        explanation="e",
        fix="f",
        line=line,
        stack=stack,
        occurrences=(Occurrence(7, line),),
        wells=tuple(WellRef("2:rack", well, "2", "rack") for well in wells),
        downstream=Downstream(0, ()),
        sources=(Source("s", "https://example.org"),),
    )


SOURCE = [
    "def run(p):",
    "    p.aspirate(10, mm)",
    "    p.dispense(10, a)",
    "    p.aspirate(10, mm)",
]


def test_it_is_the_text_of_the_line_not_its_number() -> None:
    before = fingerprint(_finding(2, ("run:2",), ("A1",)), SOURCE)
    moved = fingerprint(_finding(4, ("run:4",), ("A1",)), ["# a comment", "", *SOURCE])
    assert before == moved


def test_event_indices_and_downstream_do_not_count() -> None:
    finding = _finding(2, ("run:2",), ("A1",))
    other = replace(finding, occurrences=(Occurrence(99, 2),), severity="warning", certain=False)
    assert fingerprint(finding, SOURCE) == fingerprint(other, SOURCE)


def test_other_wells_another_rule_or_another_line_change_it() -> None:
    base = fingerprint(_finding(2, ("run:2",), ("A1",)), SOURCE)
    assert base != fingerprint(_finding(2, ("run:2",), ("A2",)), SOURCE)
    assert base != fingerprint(_finding(3, ("run:3",), ("A1",)), SOURCE)
    assert base != fingerprint(replace(_finding(2, ("run:2",), ("A1",)), rule_id="X"), SOURCE)


def test_two_lines_with_the_same_text_stay_apart() -> None:
    assert SOURCE[1] == SOURCE[3]
    first = fingerprint(_finding(2, ("run:2",), ("A1",)), SOURCE)
    second = fingerprint(_finding(4, ("run:4",), ("A1",)), SOURCE)
    assert first != second


def test_the_order_of_the_wells_does_not_count() -> None:
    assert fingerprint(_finding(2, ("run:2",), ("A1", "B1")), SOURCE) == fingerprint(
        _finding(2, ("run:2",), ("B1", "A1")), SOURCE
    )


def test_without_the_source_text_it_falls_back_to_the_line_number() -> None:
    assert fingerprint(_finding(2, ("run:2",), ("A1",)), None) != fingerprint(
        _finding(3, ("run:3",), ("A1",)), None
    )


def _edited(tmp_path: Path, name: str, old: str, new: str) -> CheckResult:
    text = BUGGY.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / name
    path.write_text(text.replace(old, new), encoding="utf-8")
    return check(path)


@pytest.mark.sim
def test_an_unrelated_edit_keeps_the_fingerprints(
    tmp_path: Path, checked: Callable[[Path], CheckResult]
) -> None:
    """A comment above `run` moves every line; a new labware and a changed delay change event
    numbers. None of it is about the findings."""
    original = checked(BUGGY)
    edited = _edited(
        tmp_path,
        "pcr_buggy.py",
        "def run(protocol: protocol_api.ProtocolContext):\n",
        "# reviewed by the lab manager\n\n\ndef run(protocol: protocol_api.ProtocolContext):\n"
        '    protocol.load_labware("nest_12_reservoir_15ml", 5)\n'
        '    protocol.comment("starting")\n',
    )
    assert [f.line for f in edited.findings] == [f.line + 5 for f in original.findings]
    assert [f.fingerprint for f in edited.findings] == [f.fingerprint for f in original.findings]


@pytest.mark.sim
def test_moving_the_finding_to_another_well_changes_it(tmp_path: Path) -> None:
    """The master mix tube is named by a variable, so the text of the root line is the same in
    both copies and only the well differs. The test is then about the wells alone."""
    text = BUGGY.read_text(encoding="utf-8").replace('rack["A1"]', "rack[MASTER_MIX]")
    results = []
    for tube in ("A1", "D6"):
        path = tmp_path / tube / "pcr_buggy.py"
        path.parent.mkdir()
        path.write_text(text.replace("SAMPLE_TUBES =", f'MASTER_MIX = "{tube}"\nSAMPLE_TUBES ='))
        results.append(check(path))
    in_a1, in_d6 = (result.findings[1] for result in results)  # the master mix line
    assert (in_a1.rule_id, in_a1.line) == (in_d6.rule_id, in_d6.line)
    assert (in_a1.wells[0].well, in_d6.wells[0].well) == ("A1", "D6")
    assert in_a1.fingerprint != in_d6.fingerprint
    # the sample tubes did not move, so the second finding keeps its fingerprint
    assert results[0].findings[0].fingerprint == results[1].findings[0].fingerprint
