"""`NebiusRunner` against the real service. Skipped unless PROVETTE_NETWORK=1 and the key is set.

What the service answered when this was last run is in `provette/sandbox/README.md`.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from provette.sandbox.nebius_runner import NebiusRunner, SandboxPermissionError

from .conftest import PLATEMAPS, PROTOCOLS

pytestmark = pytest.mark.network


def test_key_reaches_the_service_and_names_its_limits() -> None:
    runner = NebiusRunner()
    assert runner.project.startswith("aiproject-")
    who = runner.api.whoami()
    assert {"instance_max_timeout", "instance_max_concurrency"} <= set(who["limits"])


def test_buggy_protocol_round_trip() -> None:
    runner = NebiusRunner()
    platemap = json.loads((PLATEMAPS / "pcr-01.json").read_text(encoding="utf-8"))
    try:
        result = runner.run_checks(
            (PROTOCOLS / "pcr_buggy.py").read_text(encoding="utf-8"), platemap
        )
    except SandboxPermissionError as error:
        pytest.skip(f"the key has no sandbox grant: {error}")
    assert result["simulator"] == "passed"
    assert result["verify_exit"] in (1, 3) and result["check_exit"] == 1
    assert result["findings"]
    assert runner.last["round_trip_seconds"] > 0


def test_five_concurrent_runs() -> None:
    runner = NebiusRunner()
    platemap = json.loads((PLATEMAPS / "pcr-01.json").read_text(encoding="utf-8"))
    text = (PROTOCOLS / "pcr_clean.py").read_text(encoding="utf-8")
    try:
        runner.ensure_image()
    except SandboxPermissionError as error:
        pytest.skip(f"the key has no sandbox grant: {error}")
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: runner.run_checks(text, platemap), range(5)))
    assert all(r["simulator"] == "passed" for r in results)
