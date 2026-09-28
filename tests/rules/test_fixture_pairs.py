"""Validation layer 3: every rule has protocols that must fire it and near misses that must not.

`tests/fixtures/rules/<RULE-ID>/fires_*.py` must produce the rule; `near_miss_*.py` must produce
no finding of that rule. Next to each is `<name>.expected.json`, the findings frozen; after an
intended change, `PROVETTE_REGEN=1` rewrites them, and every rewritten file is reviewed by eye.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from provette.check import CheckResult
from provette.rules import RULES
from tests.rules.conftest import RULE_FIXTURES, assert_matches_frozen

RULE_IDS = [rule.rule_id for rule in RULES]
PAIRS = sorted(path for rule_id in RULE_IDS for path in (RULE_FIXTURES / rule_id).glob("*.py"))


def _id(path: Path) -> str:
    return f"{path.parent.name}/{path.stem}"


@pytest.mark.parametrize("rule_id", RULE_IDS)
def test_every_rule_has_two_that_fire_and_three_near_misses(rule_id: str) -> None:
    folder = RULE_FIXTURES / rule_id
    assert len(list(folder.glob("fires_*.py"))) >= 2
    assert len(list(folder.glob("near_miss_*.py"))) >= 3


@pytest.mark.parametrize("path", PAIRS, ids=_id)
def test_every_fixture_says_in_plain_words_what_it_tests(path: Path) -> None:
    first = path.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# WHAT THIS TESTS")
    assert ("should FIRE" in first) == path.name.startswith("fires_")
    assert ("should NOT fire" in first) == path.name.startswith("near_miss_")


def test_no_stray_files() -> None:
    for folder in RULE_FIXTURES.iterdir():
        if folder.name == "protocols" or not folder.is_dir():
            continue
        assert folder.name in RULE_IDS, f"{folder} is not the id of a rule"
        for path in folder.glob("*.py"):
            assert path.name.startswith(("fires_", "near_miss_")), path


@pytest.mark.sim
@pytest.mark.parametrize("path", PAIRS, ids=_id)
def test_fixture(path: Path, checked: Callable[[Path], CheckResult]) -> None:
    result = checked(path)
    rule_id = path.parent.name
    fired = [finding for finding in result.findings if finding.rule_id == rule_id]
    if path.name.startswith("fires_"):
        assert fired, f"{rule_id} did not fire"
    else:
        assert not fired, f"{rule_id} fired on a near miss: {fired[0].explanation}"
    assert_matches_frozen(result, path.with_suffix(".expected.json"))


@pytest.mark.sim
@pytest.mark.parametrize("path", PAIRS, ids=_id)
def test_findings_are_well_formed(path: Path, checked: Callable[[Path], CheckResult]) -> None:
    lines = checked(path).source_lines
    for finding in checked(path).findings:
        assert finding.sources, "a finding without a source"
        assert finding.fingerprint
        assert finding.line is not None and 1 <= finding.line <= len(lines)
        assert finding.occurrences and finding.occurrences[0].line == finding.line
        assert finding.wells
        assert finding.downstream.count == len(finding.downstream.wells)
        assert not set(finding.wells) & set(finding.downstream.wells)
        assert f"line {finding.line}" in finding.explanation
        for word in ("atom", "provenance", "taint", "carryover", "origin"):
            assert word not in finding.explanation.lower()
        assert finding.certain or finding.severity != "error"
