"""Flow 2 without the network: a scripted planner and a scripted agent behind the live routes.

The scripts are the ones tests/planner and tests/agent use; what is tested here is the wiring:
the password, the cap, the run directory, the stream, and that a finished run reads back like a
gallery episode.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api import live as live_module
from api.main import create_app
from api.settings import REPO, Settings
from tests.api.conftest import make_settings

FILE = (REPO / "tests/fixtures/protocols/pcr_buggy.py").read_text()
PCR_MAP = json.loads((REPO / "eval/platemaps/pcr-01.json").read_text())
CLEAN = {"simulator": "passed", "simulator_error": "", "verify_exit": 0, "verify_text": "ok",
         "verify": {}, "check_exit": 0, "check_text": "clean", "findings": [],
         "seconds": 0.1}  # fmt: skip
PASSWORD = "judge-secret"


def call(name: str, arguments: Any = None) -> dict[str, Any]:
    return {
        "id": f"call_{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments or {})},
    }


def turn(*calls: dict[str, Any], tokens: int = 100) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": "", "reasoning": "hmm"}
    if calls:
        message["tool_calls"] = list(calls)
    return {
        "message": message,
        "usage": {"prompt_tokens": 1000, "completion_tokens": tokens},
        "finish_reason": "tool_calls" if calls else "stop",
    }


class Scripted:
    """A model that plays its turns in order; the planner's script proposes, the agent's writes."""

    def __init__(self, *turns: dict[str, Any], delay_s: float = 0.0) -> None:
        self.turns = list(turns)
        self.delay_s = delay_s

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        time.sleep(self.delay_s)
        names = [t["function"]["name"] for t in tools]
        if "propose_platemap" in names:
            return turn(call("propose_platemap", {"platemap": PCR_MAP}))
        if not self.turns:
            raise AssertionError("the script ran out")
        return self.turns.pop(0)


class ScriptedRunner:
    name = "scripted"

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        return dict(CLEAN)

    def close(self) -> None:
        pass


def live_settings(tmp_path: Path, password: str = PASSWORD) -> Settings:
    base = make_settings(tmp_path)
    return Settings(
        **{
            **base.__dict__,
            "api_key": "k",
            "base_url": "http://x",
            "judge_password": password,
            "daily_cap_usd": 1.0,
        }
    )


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(live_settings(tmp_path))
    app.state.live = live_module.Live(
        app.state.settings,
        app.state.gallery,
        chat_factory=lambda model: Scripted(
            turn(call("platemap")),
            turn(call("write_protocol", {"text": FILE})),
            turn(call("submit")),
            delay_s=0.2,
        ),
        runner_factory=ScriptedRunner,
    )
    with TestClient(app) as c:
        yield c


def test_the_flow_is_off_without_a_key_or_password(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as c:
        assert c.get("/api/live").json()["enabled"] is False
        r = c.post("/api/plan", json={"request": "x"})
        assert r.status_code == 503 and "off" in r.json()["detail"]


def test_the_password_guards_planning_and_running(client: TestClient) -> None:
    status = client.get("/api/live").json()
    assert status["enabled"] is True and status["cap_usd"] == 1.0
    assert any(e["id"] == "pcr-01" for e in status["examples"])
    assert client.post("/api/plan", json={"request": "x"}).status_code == 401
    assert (
        client.post(
            "/api/plan", json={"request": "x"}, headers={"x-judge-password": "no"}
        ).status_code
        == 401
    )


def test_plan_returns_the_proposed_map_and_counts_the_spend(client: TestClient) -> None:
    # The planner refuses a map whose volumes are not in the request, so the request is real.
    r = client.post(
        "/api/plan", json={"request": PCR_MAP["request"]}, headers={"x-judge-password": PASSWORD}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["platemap"]["liquids"][0]["name"] == "master_mix"
    assert body["error"] is None and body["stop_reason"] == "proposed"
    assert body["cost_usd"] is not None and body["cost_usd"] > 0
    assert client.get("/api/live").json()["spent_today_usd"] == pytest.approx(
        body["cost_usd"], abs=1e-4
    )


def test_a_run_streams_its_steps_and_ends_as_a_gallery_episode(client: TestClient) -> None:
    headers = {"x-judge-password": PASSWORD}
    r = client.post(
        "/api/runs", json={"request": "PCR for 8 samples", "platemap": PCR_MAP}, headers=headers
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["id"]
    # The stream: snapshots as the transcript grows, then done.
    events: list[dict[str, Any]] = []
    with client.stream("GET", f"/api/runs/{run_id}/events") as stream:
        kind = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                events.append({"event": kind, "data": json.loads(line[6:])})
                if kind == "done":
                    break
    assert events[-1]["event"] == "done" and events[-1]["data"]["state"] == "done"
    snapshots = [e["data"] for e in events if e["event"] == "snapshot"]
    assert len(snapshots) >= 2, "the steps arrive before the end"
    final = snapshots[-1]
    assert final["state"] == "done" and final["verified"] is True
    titles = [s["title"] for s in final["steps"]]
    assert titles[0] == "Read the plate map" and titles[-1] == "Submitted draft 0"
    assert final["cost_usd"] is not None and final["request"] == "PCR for 8 samples"
    # And it reads back like any episode.
    row = client.get(f"/api/runs/{run_id}").json()
    assert row["state"] == "done" and row["outcome"]["verified"] is True
    assert row["platemap"]["id"] == "pcr-01" and [d["n"] for d in row["draft_rows"]] == [0]
    assert client.get(f"/api/runs/{run_id}/protocol.py").text == FILE
    assert client.get(f"/api/runs/{run_id}/drafts/0").json()["text"] == FILE
    assert client.get("/api/live").json()["spent_today_usd"] > 0
    assert client.get("/api/runs/nope").status_code == 404


def test_the_daily_cap_turns_the_flow_off_with_a_sentence(client: TestClient) -> None:
    client.app.state.live.ledger.add(1.0)  # type: ignore[attr-defined]
    r = client.post("/api/plan", json={"request": "x"}, headers={"x-judge-password": PASSWORD})
    assert r.status_code == 503 and "paused for today" in r.json()["detail"]
    r = client.post(
        "/api/runs",
        json={"request": "x", "platemap": PCR_MAP},
        headers={"x-judge-password": PASSWORD},
    )
    assert r.status_code == 503


def test_an_invalid_platemap_is_refused(client: TestClient) -> None:
    r = client.post(
        "/api/runs",
        json={"request": "x", "platemap": {"id": "x"}},
        headers={"x-judge-password": PASSWORD},
    )
    assert r.status_code == 422 and "not valid" in r.json()["detail"]


def test_a_plan_job_streams_the_planners_turns_and_ends_with_the_map(client: TestClient) -> None:
    headers = {"x-judge-password": PASSWORD}
    assert client.post("/api/plans", json={"request": "x"}).status_code == 401
    r = client.post(
        "/api/plans",
        json={"request": PCR_MAP["request"], "technique": "PCR setup"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    plan_id = r.json()["id"]
    events: list[dict[str, Any]] = []
    with client.stream("GET", f"/api/plans/{plan_id}/events") as stream:
        kind = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                events.append({"event": kind, "data": json.loads(line[6:])})
                if kind == "done":
                    break
    assert events[-1]["event"] == "done" and events[-1]["data"]["state"] == "done"
    final = [e["data"] for e in events if e["event"] == "snapshot"][-1]
    assert final["state"] == "done" and final["stop_reason"] == "proposed"
    assert final["platemap"]["liquids"][0]["name"] == "master_mix"
    assert final["technique"] == "PCR setup" and final["request"] == PCR_MAP["request"]
    assert [s["tool"] for s in final["steps"]] == ["propose_platemap"]
    assert final["steps"][0]["title"] == "Proposed the plate map"
    assert final["cost_usd"] is not None and final["cost_usd"] > 0
    row = client.get(f"/api/plans/{plan_id}").json()
    assert row["state"] == "done" and row["platemap"]["id"] == "planned"
    assert client.get("/api/plans/nope").status_code == 404


def test_the_plans_are_listed_newest_first_with_their_outcome(client: TestClient) -> None:
    headers = {"x-judge-password": PASSWORD}
    live_module.plan_limit._calls.clear()
    assert client.get("/api/plans").json()["plans"] == []
    first = client.post(
        "/api/plans",
        json={"request": PCR_MAP["request"], "technique": "PCR setup"},
        headers=headers,
    ).json()["id"]
    with client.stream("GET", f"/api/plans/{first}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("event: done"):
                break
    time.sleep(0.01)  # the second plan's `created` must sort after the first's
    second = client.post(
        "/api/plans", json={"request": "x", "anyway": True}, headers=headers
    ).json()["id"]
    rows = client.get("/api/plans").json()["plans"]
    assert [r["id"] for r in rows][:2] == [second, first]
    done = next(r for r in rows if r["id"] == first)
    assert done["state"] == "done" and done["outcome"] == "proposed"
    assert done["technique"] == "PCR setup" and done["request"] == PCR_MAP["request"]
    assert done["tool_calls"] == 1 and done["cost_usd"] > 0
    assert set(done) == {
        "id", "request", "technique", "created", "state", "outcome", "tool_calls", "cost_usd"
    }  # fmt: skip
    # A plan that ended without a map says so, in the same word the page shows.
    folder = client.app.state.live.plan_ref(second)  # type: ignore[attr-defined]
    with client.stream("GET", f"/api/plans/{second}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("event: done"):
                break
    (folder / "result.json").write_text(
        json.dumps({"platemap": None, "stop_reason": "call budget"})
    )
    (folder / "status.json").write_text(json.dumps({"state": "done"}))
    rows = {r["id"]: r for r in client.get("/api/plans").json()["plans"]}
    assert rows[second]["outcome"] == "no map"
    (folder / "status.json").write_text(json.dumps({"state": "failed", "error": "x"}))
    assert {r["id"]: r for r in client.get("/api/plans").json()["plans"]}[second][
        "outcome"
    ] == "failed"
    # The planner said the message asks for no liquid handling: its own word, and the sentence.
    (folder / "result.json").write_text(
        json.dumps({"platemap": None, "stop_reason": "not a request", "declined": "A question."})
    )
    (folder / "status.json").write_text(json.dumps({"state": "done"}))
    assert {r["id"]: r for r in client.get("/api/plans").json()["plans"]}[second][
        "outcome"
    ] == "not a request"
    assert client.get(f"/api/plans/{second}").json()["declined"] == "A question."


def test_a_message_with_no_lab_word_is_refused_before_any_model_call(client: TestClient) -> None:
    """The gate answers at once, with a code the page recognises; `anyway` goes past it."""
    headers = {"x-judge-password": PASSWORD}
    live_module.plan_limit._calls.clear()
    before = len(client.get("/api/plans").json()["plans"])
    r = client.post(
        "/api/plans",
        json={"request": "What is your name and what is the purpose of life?"},
        headers=headers,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "not_a_request"
    assert "liquid-handling request" in r.json()["detail"]["message"]
    assert len(client.get("/api/plans").json()["plans"]) == before  # nothing was started
    r = client.post(
        "/api/plans",
        json={"request": "What is your name and what is the purpose of life?", "anyway": True},
        headers=headers,
    )
    assert r.status_code == 200, r.text


def test_the_live_runs_are_listed_newest_first(client: TestClient) -> None:
    headers = {"x-judge-password": PASSWORD}
    live_module.run_limit._calls.clear()  # the limit is per process; earlier tests started runs
    assert client.get("/api/runs").json()["runs"] == []
    r = client.post(
        "/api/runs",
        json={"request": "PCR for 8 samples", "platemap": PCR_MAP, "technique": "PCR setup"},
        headers=headers,
    )
    run_id = r.json()["id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("event: done"):
                break
    rows = client.get("/api/runs").json()["runs"]
    assert [row["run_id"] for row in rows] == [run_id]
    assert rows[0]["state"] == "done" and rows[0]["verified"] is True
    assert rows[0]["technique"] == "PCR setup" and rows[0]["id"] == f"runs/live/{run_id}"
    assert rows[0]["run_label"] == "live, on this deployment" and rows[0]["condition"] == "plain"
    snap = client.get(f"/api/runs/{run_id}").json()
    assert snap["created"] is not None and snap["steps"][0]["reasoning"] == "hmm"


class Counting:
    """A slow model that would call a calculator for ever: how many times it was asked is the
    proof that a stop lands before the next call."""

    def __init__(self, delay_s: float = 0.4) -> None:
        self.delay_s = delay_s
        self.calls = 0

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self.calls += 1
        time.sleep(self.delay_s)
        names = [t["function"]["name"] for t in tools]
        if "propose_platemap" in names:
            return turn(call("labware", {"kind": "plate"}))
        return turn(call("platemap"))


def _wait_for_first_call(model: Counting) -> None:
    """Until the model is inside its first (slow) call: a stop posted now lands mid-way."""
    for _ in range(100):
        if model.calls:
            return
        time.sleep(0.02)
    raise AssertionError("the model was never called")


def _stream_to_done(client: TestClient, url: str) -> dict[str, Any]:
    last: dict[str, Any] = {}
    with client.stream("GET", url) as stream:
        kind = None
        for line in stream.iter_lines():
            if line.startswith("event: "):
                kind = line[7:]
            elif line.startswith("data: "):
                if kind == "snapshot":
                    last = json.loads(line[6:])
                elif kind == "done":
                    last["_done"] = json.loads(line[6:])
                    break
    return last


def test_a_plan_stopped_mid_way_ends_stopped_and_calls_nothing_more(tmp_path: Path) -> None:
    model = Counting()
    app = create_app(live_settings(tmp_path))
    app.state.live = live_module.Live(
        app.state.settings, app.state.gallery, chat_factory=lambda m: model
    )
    headers = {"x-judge-password": PASSWORD}
    live_module.plan_limit._calls.clear()
    with TestClient(app) as client:
        plan_id = client.post(
            "/api/plans", json={"request": "x", "anyway": True}, headers=headers
        ).json()["id"]
        _wait_for_first_call(model)
        assert client.post(f"/api/plans/{plan_id}/stop").status_code == 401
        r = client.post(f"/api/plans/{plan_id}/stop", headers=headers)
        assert r.status_code == 200 and r.json() == {"id": plan_id, "state": "stopping"}
        snap = _stream_to_done(client, f"/api/plans/{plan_id}/events")
        assert snap["_done"] == {"state": "stopped"} and snap["state"] == "stopped"
        assert snap["stop_reason"] == "stopped by the user" and snap["platemap"] is None
        assert model.calls == 1, "the stop landed during the first model call; no second one"
        assert snap["tool_calls"] == 0 and snap["tokens_in"] == 1000
        assert snap["cost_usd"] > 0 and client.get("/api/live").json()["spent_today_usd"] > 0
        row = client.get(f"/api/plans/{plan_id}").json()
        assert row["state"] == "stopped" and len(row["steps"]) == 1
        listed = client.get("/api/plans").json()["plans"][0]
        assert listed["state"] == "stopped" and listed["outcome"] == "stopped"
        # Stopping again, or stopping a plan that has ended, is a 409 in a sentence.
        r = client.post(f"/api/plans/{plan_id}/stop", headers=headers)
        assert r.status_code == 409 and "already ended" in r.json()["detail"]
        assert client.post("/api/plans/nope/stop", headers=headers).status_code == 404


def test_a_run_stopped_mid_way_ends_stopped_with_the_steps_so_far(tmp_path: Path) -> None:
    model = Counting()
    app = create_app(live_settings(tmp_path))
    app.state.live = live_module.Live(
        app.state.settings,
        app.state.gallery,
        chat_factory=lambda m: model,
        runner_factory=ScriptedRunner,
    )
    headers = {"x-judge-password": PASSWORD}
    live_module.run_limit._calls.clear()
    with TestClient(app) as client:
        run_id = client.post(
            "/api/runs", json={"request": "PCR for 8 samples", "platemap": PCR_MAP}, headers=headers
        ).json()["id"]
        _wait_for_first_call(model)
        r = client.post(f"/api/runs/{run_id}/stop", headers=headers)
        assert r.status_code == 200 and r.json()["state"] == "stopping"
        snap = _stream_to_done(client, f"/api/runs/{run_id}/events")
        assert snap["_done"] == {"state": "stopped"} and snap["state"] == "stopped"
        assert model.calls == 1
        assert snap["done"]["stop_reason"] == "stopped by the user"
        assert snap["done"]["tool_calls"] == 0 and snap["done"]["tokens_in"] == 1000
        assert len(snap["steps"]) == 1 and snap["verified"] is False
        assert snap["cost_usd"] > 0 and client.get("/api/live").json()["spent_today_usd"] > 0
        assert client.get(f"/api/runs/{run_id}").json()["state"] == "stopped"
        assert client.get("/api/runs").json()["runs"][0]["state"] == "stopped"
        r = client.post(f"/api/runs/{run_id}/stop", headers=headers)
        assert r.status_code == 409


class Gate:
    """A model whose runs wait at a gate until the test opens it, and whose plans answer at once:
    two runs held open fill the run threads, and a plan must still go through."""

    def __init__(self) -> None:
        import threading

        self.open = threading.Event()
        self.waiting = 0

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        names = [t["function"]["name"] for t in tools]
        if "propose_platemap" in names:
            return turn(call("propose_platemap", {"platemap": PCR_MAP}))
        self.waiting += 1
        self.open.wait(timeout=10)
        return turn(call("submit"))


def test_a_plan_goes_through_while_two_runs_hold_every_run_thread(tmp_path: Path) -> None:
    """Plans have their own threads: a judge's third chat plans at once instead of waiting in a
    queue behind two runs, a third run is told plainly to wait, and too many plans are too."""
    model = Gate()
    app = create_app(live_settings(tmp_path))
    app.state.live = live_module.Live(
        app.state.settings,
        app.state.gallery,
        chat_factory=lambda m: model,
        runner_factory=ScriptedRunner,
    )
    headers = {"x-judge-password": PASSWORD}
    live_module.run_limit._calls.clear()
    live_module.plan_limit._calls.clear()
    try:
        with TestClient(app) as client:
            body = {"request": "PCR for 8 samples", "platemap": PCR_MAP}
            for _ in range(live_module.MAX_RUNS_AT_ONCE):
                assert client.post("/api/runs", json=body, headers=headers).status_code == 200
            for _ in range(100):
                if model.waiting >= live_module.MAX_RUNS_AT_ONCE:
                    break
                time.sleep(0.02)
            assert model.waiting == live_module.MAX_RUNS_AT_ONCE  # both run threads are held
            r = client.post("/api/runs", json=body, headers=headers)
            assert r.status_code == 503 and "running already" in r.json()["detail"]
            plan_id = client.post(
                "/api/plans", json={"request": PCR_MAP["request"]}, headers=headers
            ).json()["id"]
            snap = _stream_to_done(client, f"/api/plans/{plan_id}/events")
            assert snap["state"] == "done" and snap["stop_reason"] == "proposed"
            assert snap["platemap"] is not None
            assert client.get("/api/live").json()["running"] == live_module.MAX_RUNS_AT_ONCE
            # every plan thread busy: the next plan is told, not queued
            app.state.live._planning.update(
                f"busy{k}" for k in range(live_module.MAX_PLANS_AT_ONCE)
            )
            r = client.post(
                "/api/plans", json={"request": "PCR for 8 samples", "anyway": True}, headers=headers
            )
            assert r.status_code == 503 and "plans are being written already" in r.json()["detail"]
            app.state.live._planning.clear()
            model.open.set()
    finally:
        model.open.set()
