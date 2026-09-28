"""`DockerRunner` against the built image. Skipped unless Docker is usable and the image exists."""

from __future__ import annotations

import json

import pytest

from provette.sandbox.docker_runner import DockerRunner

from .conftest import PLATEMAPS, PROTOCOLS

pytestmark = pytest.mark.docker


def test_buggy_protocol_round_trip() -> None:
    runner = DockerRunner()
    platemap = json.loads((PLATEMAPS / "pcr-01.json").read_text(encoding="utf-8"))
    result = runner.run_checks((PROTOCOLS / "pcr_buggy.py").read_text(encoding="utf-8"), platemap)
    runner.close()
    assert result["simulator"] == "passed"
    assert result["verify_exit"] in (1, 3) and result["check_exit"] == 1
    assert result["findings"]


def test_rejected_protocol_is_reported_not_raised() -> None:
    runner = DockerRunner()
    platemap = json.loads((PLATEMAPS / "pcr-01.json").read_text(encoding="utf-8"))
    result = runner.run_checks(
        (PROTOCOLS / "bad_protocol.py").read_text(encoding="utf-8"), platemap
    )
    assert result["simulator"] == "rejected" and result["verify_exit"] == 2
