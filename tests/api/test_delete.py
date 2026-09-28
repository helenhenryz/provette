"""Deleting from the history: a run, a plan or a check leaves the deployment for everyone, only
with the judge password, and a job still under way is refused until it is stopped."""

from __future__ import annotations

import json
import threading
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import make_settings

PASSWORD = "the judge"


def _client(tmp_path: Path) -> TestClient:
    settings = replace(make_settings(tmp_path, sets=()), judge_password=PASSWORD)
    return TestClient(create_app(settings))


def _record(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "request.json").write_text(json.dumps({"request": "x"}), encoding="utf-8")
    return folder


def test_a_check_a_plan_and_a_run_are_deleted_with_the_password(tmp_path: Path) -> None:
    client = _client(tmp_path)
    data = tmp_path / "data"
    check, plan, run = (
        _record(data / "checks" / "chk1"),
        _record(data / "plans" / "pl1"),
        _record(data / "runs" / "rn1"),
    )
    for path in ("/api/checks/chk1", "/api/plans/pl1", "/api/runs/rn1"):
        assert client.delete(path).status_code == 401  # no password, nothing removed
    assert check.is_dir() and plan.is_dir() and run.is_dir()
    headers = {"x-judge-password": PASSWORD}
    for path in ("/api/checks/chk1", "/api/plans/pl1", "/api/runs/rn1"):
        assert client.delete(path, headers=headers).json()["deleted"] is True
    assert not check.exists() and not plan.exists() and not run.exists()
    assert client.delete("/api/runs/rn1", headers=headers).status_code == 404
    assert client.delete("/api/checks/..", headers=headers).status_code in (404, 405)


def test_a_job_still_under_way_is_refused(tmp_path: Path) -> None:
    client = _client(tmp_path)
    run = _record(tmp_path / "data" / "runs" / "rn2")
    live = client.app.state.live  # type: ignore[attr-defined]
    with live._lock:
        live._stops["rn2"] = threading.Event()
    answer = client.delete("/api/runs/rn2", headers={"x-judge-password": PASSWORD})
    assert answer.status_code == 409 and "Stop it first" in answer.json()["detail"]
    assert run.is_dir()
