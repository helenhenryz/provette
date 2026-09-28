"""The unlock dialog's check: the right password is let in, a wrong one is told so at once, and a
deployment with no password says that instead."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import make_settings


def client(tmp_path: Path, password: str) -> TestClient:
    return TestClient(create_app(replace(make_settings(tmp_path), judge_password=password)))


def test_the_right_password_is_let_in_and_a_wrong_one_is_not(tmp_path: Path) -> None:
    with client(tmp_path, "amber-pipette-harbor-42") as c:
        ok = c.post("/api/judge", headers={"X-Judge-Password": "amber-pipette-harbor-42"})
        assert ok.status_code == 204
        wrong = c.post("/api/judge", headers={"X-Judge-Password": "amber"})
        assert wrong.status_code == 401
        assert "wrong" in wrong.json()["detail"]
        assert c.post("/api/judge").status_code == 401


def test_a_deployment_with_no_password_says_so(tmp_path: Path) -> None:
    with client(tmp_path, "") as c:
        r = c.post("/api/judge", headers={"X-Judge-Password": "anything"})
        assert r.status_code == 503
        assert "none set" in r.json()["detail"]
