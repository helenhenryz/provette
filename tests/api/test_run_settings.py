"""The Settings page's budgets: the defaults are the code's constants, a change needs the judge
key and stays in range, Reset brings the defaults back, and the live jobs run with the values
saved, not with the constants."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import live as live_module
from api.main import create_app
from api.run_settings import DEFAULTS, LIVE_MIN_DRAFTS
from provette.agent import loop as agent_loop
from provette.planner import loop as planner_loop
from tests.api.test_live import PASSWORD, PCR_MAP, live_settings

KEY = {"x-judge-password": PASSWORD}


@pytest.fixture
def client(tmp_path: Path) -> Any:
    with TestClient(create_app(live_settings(tmp_path))) as c:
        yield c


def test_the_defaults_are_the_constants_the_code_runs_with() -> None:
    assert DEFAULTS == {
        "run_tool_calls": agent_loop.MAX_TOOL_CALLS,
        "run_tokens": agent_loop.MAX_COMPLETION_TOKENS,
        "run_min_drafts": LIVE_MIN_DRAFTS,
        "plan_tool_calls": planner_loop.MAX_TOOL_CALLS,
        "plan_tokens": planner_loop.MAX_COMPLETION_TOKENS,
    }
    assert DEFAULTS["run_tool_calls"] == 25 and DEFAULTS["run_min_drafts"] == 3


def test_change_needs_the_key_stays_in_range_and_resets(client: TestClient) -> None:
    rows = client.get("/api/run-settings").json()["settings"]
    assert {r["key"]: r["value"] for r in rows} == DEFAULTS
    assert all(r["low"] <= r["default"] <= r["high"] for r in rows)
    assert client.put("/api/run-settings", json={"run_tokens": 50000}).status_code == 401
    r = client.put("/api/run-settings", json={"run_tokens": 50000}, headers=KEY)
    assert r.status_code == 200
    assert {x["key"]: x["value"] for x in r.json()["settings"]}["run_tokens"] == 50000
    for bad in ({"run_tokens": 10}, {"run_tokens": "a lot"}, {"nope": 3}, {"run_min_drafts": True}):
        assert client.put("/api/run-settings", json=bad, headers=KEY).status_code == 422, bad
    # a refused change leaves the saved one alone
    values = {x["key"]: x["value"] for x in client.get("/api/run-settings").json()["settings"]}
    assert values["run_tokens"] == 50000
    assert client.delete("/api/run-settings").status_code == 401
    r = client.delete("/api/run-settings", headers=KEY)
    assert {x["key"]: x["value"] for x in r.json()["settings"]} == DEFAULTS


def _wait(folder: Path) -> None:
    for _ in range(100):
        if (folder / "status.json").is_file() and '"running"' not in (
            folder / "status.json"
        ).read_text():
            return
        time.sleep(0.05)


def test_the_live_jobs_run_with_the_saved_values(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, dict[str, Any]] = {}

    def fake_plan(*args: Any, **kwargs: Any) -> Any:
        seen["plan"] = kwargs
        raise RuntimeError("stop here")

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        seen["run"] = kwargs
        raise RuntimeError("stop here")

    monkeypatch.setattr(live_module, "plan", fake_plan)
    monkeypatch.setattr(live_module, "run_episode", fake_run)
    live_module.plan_limit._calls.clear()
    live_module.run_limit._calls.clear()
    changes = {
        "run_tool_calls": 7,
        "run_tokens": 30000,
        "run_min_drafts": 1,
        "plan_tool_calls": 4,
        "plan_tokens": 12000,
    }
    assert client.put("/api/run-settings", json=changes, headers=KEY).status_code == 200
    live = client.app.state.live  # type: ignore[attr-defined]
    plan_id = client.post("/api/plans", json={"request": PCR_MAP["request"]}, headers=KEY).json()[
        "id"
    ]
    _wait(live.plan_ref(plan_id))
    r = client.post(
        "/api/runs", json={"request": PCR_MAP["request"], "platemap": PCR_MAP}, headers=KEY
    )
    assert r.status_code == 200, r.text
    for _ in range(100):
        if "run" in seen:
            break
        time.sleep(0.05)
    assert seen["plan"]["max_tool_calls"] == 4 and seen["plan"]["max_completion_tokens"] == 12000
    assert seen["run"]["max_tool_calls"] == 7 and seen["run"]["max_completion_tokens"] == 30000
    assert seen["run"]["min_drafts"] == 1
