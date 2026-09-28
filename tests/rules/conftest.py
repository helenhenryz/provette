"""Shared helpers: each protocol is run through `check` at most once per test process.

The simulator takes 2 to 4 seconds per protocol. Tests ask for `checked(path)`; the cache lives
for the whole session, so ten assertions about one fixture cost one simulator run.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from provette.check import CheckResult, check
from provette.rules import Finding

FIXTURES = Path(__file__).parent.parent / "fixtures"
RULE_FIXTURES = FIXTURES / "rules"
PROTOCOLS = FIXTURES / "protocols"
REGEN = os.environ.get("PROVETTE_REGEN") == "1"

_cache: dict[Path, CheckResult] = {}


def check_once(path: Path) -> CheckResult:
    if path not in _cache:
        _cache[path] = check(path)
    return _cache[path]


@pytest.fixture(scope="session")
def checked() -> Callable[[Path], CheckResult]:
    return check_once


def reduced(finding: Finding) -> dict[str, Any]:
    """What is frozen in `<name>.expected.json`: enough to notice any drift, little enough to
    review by eye."""
    return {
        "rule_id": finding.rule_id,
        "severity": finding.severity,
        "certain": finding.certain,
        "line": finding.line,
        "wells": [well.key for well in finding.wells],
        "downstream": finding.downstream.count,
        "fingerprint": finding.fingerprint,
    }


def assert_matches_frozen(result: CheckResult, expected_path: Path) -> None:
    """Compare with the frozen file; `PROVETTE_REGEN=1` rewrites it instead (then review it)."""
    actual = [reduced(finding) for finding in result.findings]
    if REGEN:
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
    assert expected_path.is_file(), f"{expected_path} is missing: run with PROVETTE_REGEN=1"
    assert actual == json.loads(expected_path.read_text(encoding="utf-8"))
