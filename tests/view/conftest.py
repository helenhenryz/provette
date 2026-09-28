"""Each fixture protocol goes through the simulator once per test process."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from provette.check import CheckResult, check

PROTOCOLS = Path(__file__).parents[1] / "fixtures" / "protocols"
PLATEMAPS = Path(__file__).parents[2] / "eval" / "platemaps"

_cache: dict[Path, CheckResult] = {}


def check_once(path: Path) -> CheckResult:
    if path not in _cache:
        _cache[path] = check(path)
    return _cache[path]


@pytest.fixture(scope="session")
def checked() -> Callable[[Path], CheckResult]:
    return check_once
