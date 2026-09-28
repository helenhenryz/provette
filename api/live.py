"""Run your own: the loop, live. The planner proposes the plate map; the person approves it;
the episode runs on the hosted model with every tool call streaming in as it happens.

    GET  /api/live                    is the flow on, the model, today's spend against the cap,
                                      the example requests
    POST /api/plan                    {"request": str} -> the proposal (password needed)
    POST /api/plans                   {"request", "technique"?} -> {"id"}: the same planning,
                                      as a job whose turns stream (password needed)
    GET  /api/plans                   this deployment's plans, newest first, a small row each
    GET  /api/plans/{id}              the planning so far: steps, and the map once proposed
    GET  /api/plans/{id}/events       server-sent events: the planner's turns, then "done"
    POST /api/plans/{id}/stop         stop the planning before its next model call (password)
    GET  /api/runs                    the live runs on this deployment, newest first, as cards
    POST /api/runs                    {"request": str, "platemap": dict} -> {"id"} (password)
    GET  /api/runs/{id}               the episode so far, in the gallery's shape, plus "state"
    GET  /api/runs/{id}/events        server-sent events: the steps as they land, then "done"
    POST /api/runs/{id}/stop          stop the episode before its next model call or check
    GET  /api/runs/{id}/analysis      check, verify and the replay of the final draft
    GET  /api/runs/{id}/replay.html   `provette view`'s page
    GET  /api/runs/{id}/protocol.py   the final draft
    GET  /api/runs/{id}/drafts/{n}    one draft and its checks

The backend wraps and never reimplements: `provette.planner.loop.plan` proposes the map;
`provette.agent.loop.run_episode` with `LocalRunner` runs the episode into <data_dir>/runs/<id>/,
exactly as `eval/agent/run.py` does, so the run's directory is an episode like any in the gallery
and the same reading code shows it. The stream is a tail of the `transcript.jsonl` the loop
writes, plus "thinking" marks from a wrapper around the chat call: no change to the loop.

The password is the judge's (`PROVETTE_JUDGE_PASSWORD`, header `X-Judge-Password`); the rules
allow credentials for a demo. Rate limits per address, two runs at a time in all, and a daily
spend cap that turns the flow off with a sentence (`api/ledger.py`).
"""

from __future__ import annotations

import json
import logging
import secrets
import shutil
import threading
import time
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import anyio
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.analysis import AnalysisError
from api.auth import require_judge_password
from api.episodes import EpisodeRef, Gallery, runner_label
from api.ledger import Ledger
from api.limits import RateLimit, client_key
from api.replay_page import replay_page
from api.run_settings import LIVE_MIN_DRAFTS as LIVE_MIN_DRAFTS  # re-exported: D-32
from api.run_settings import RunSettings
from api.settings import Settings
from api.steps import steps_from_transcript
from provette.agent.llm import Chat, OpenAIChat
from provette.agent.loop import STOPPED_BY_USER, run_episode
from provette.agent.runner import Runner
from provette.intent.spec import PlateMapError, dump_platemap, platemap_from_dict
from provette.planner.gate import NOT_A_REQUEST as NOT_A_REQUEST_WORDS
from provette.planner.gate import looks_like_lab_request
from provette.planner.loop import plan

router = APIRouter(prefix="/api", tags=["live"])
log = logging.getLogger(__name__)

RUN_MODEL = "nvidia/nemotron-3-super-120b-a12b"
# A live run's model may not submit a draft the checks reject before this many drafts (D-32): the
# evaluation took any submit, and one live run gave up on its first failing draft.
PLAN_ESTIMATE_USD = 0.01  # a plan on Super costs well under a cent (eval/planner)
RUN_ESTIMATE_USD = 0.10  # a run on Super costs a few cents (eval/agent); a long one more
MAX_REQUEST_CHARS = 2000
MAX_RUNS_AT_ONCE = 2
# Plans are model calls only, no simulator, so more can go at once; they have their own threads,
# so a plan never waits behind two runs and a run never waits behind plans
MAX_PLANS_AT_ONCE = 4
LIST_AT_MOST = 50  # rows the lists of runs and plans serve
ENDED = ("done", "failed", "stopped")  # the states after which a record no longer changes
plan_limit = RateLimit(n=6, per_s=600)
run_limit = RateLimit(n=3, per_s=600)

ChatFactory = Callable[[str], Chat]  # model -> a chat callable
RunnerFactory = Callable[[], Runner]


class PlanRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=MAX_REQUEST_CHARS)
    technique: str | None = Field(None, max_length=60)
    # the person said "plan it anyway": no gate, and the model is not offered not_a_request
    anyway: bool = False


class RunRequest(BaseModel):
    request: str = Field(..., min_length=1, max_length=MAX_REQUEST_CHARS)
    platemap: dict[str, Any]
    technique: str | None = Field(None, max_length=60)


# ---------------------------------------------------------------------------------------------
# The live service
# ---------------------------------------------------------------------------------------------


class EventChat:
    """The chat call, with a mark in events.jsonl before and after each model turn, so the page
    can say 'the model is thinking' between tool calls."""

    def __init__(self, inner: Chat, events: Path) -> None:
        self.inner = inner
        self.events = events

    def _mark(self, kind: str) -> None:
        with self.events.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"type": kind, "at": time.time()}) + "\n")

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self._mark("thinking")
        try:
            return self.inner(messages, tools)
        finally:
            self._mark("replied")


class RecordingChat:
    """The chat call for a planning job: every turn is written to transcript.jsonl as it
    happens, in the shape `steps_from_transcript` reads, so the page can show the planner's
    tool calls while it thinks. A turn's results are known one call later (the loop puts
    them in the next call's messages), so the file is rewritten whole each time; it is small."""

    def __init__(self, inner: Chat, folder: Path) -> None:
        self.inner = inner
        self.folder = folder
        self.turns: list[dict[str, Any]] = []

    def _mark(self, kind: str) -> None:
        with (self.folder / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"type": kind, "at": time.time()}) + "\n")

    def _write(self) -> None:
        text = "".join(json.dumps(t) + "\n" for t in self.turns)
        (self.folder / "transcript.jsonl").write_text(text, encoding="utf-8")

    def _fill_results(self, messages: list[dict[str, Any]]) -> None:
        """The last turn's tool results, read back from the messages the loop built."""
        if not self.turns:
            return
        last = self.turns[-1]
        by_id = {c["id"]: c["name"] for c in last["assistant"].get("tool_calls", [])}
        results = []
        for m in reversed(messages):
            if m.get("role") == "assistant":
                break
            if m.get("role") == "tool" and m.get("tool_call_id") in by_id:
                try:
                    result = json.loads(str(m.get("content") or "{}"))
                except json.JSONDecodeError:
                    result = {}
                results.append({"name": by_id[m["tool_call_id"]], "result": result})
        last["tool_results"] = list(reversed(results))

    def __call__(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> dict[str, Any]:
        self._fill_results(messages)
        self._write()
        self._mark("thinking")
        started = time.time()
        try:
            reply = self.inner(messages, tools)
        finally:
            self._mark("replied")
        message = reply.get("message") or {}
        calls = [c for c in (message.get("tool_calls") or []) if c.get("function")]
        self.turns.append(
            {
                "turn": len(self.turns),
                "seconds": round(time.time() - started, 1),
                "finish_reason": reply.get("finish_reason"),
                "assistant": {
                    "content": message.get("content") or "",
                    "reasoning": message.get("reasoning") or message.get("reasoning_content"),
                    "tool_calls": [
                        {
                            "id": c.get("id") or f"call_{len(self.turns)}_{n}",
                            "name": c["function"].get("name") or "",
                            "arguments": c["function"].get("arguments") or "{}",
                        }
                        for n, c in enumerate(calls)
                    ],
                },
                "tool_results": [],
                "usage": reply.get("usage") or {},
            }
        )
        self._write()
        return reply


class Live:
    def __init__(
        self,
        settings: Settings,
        gallery: Gallery,
        chat_factory: ChatFactory | None = None,
        runner_factory: RunnerFactory | None = None,
        model: str = RUN_MODEL,
    ) -> None:
        self.settings = settings
        self.gallery = gallery
        self.model = model
        self.ledger = Ledger(settings.data_dir / "spend.json", settings.daily_cap_usd)
        # the budgets a person may change on the Settings page; each job reads them as it starts
        self.run_settings = RunSettings(settings.data_dir / "run-settings.json")
        self.chat_factory = chat_factory or self._default_chat
        self.runner_factory = runner_factory or self._default_runner
        self.pool = ThreadPoolExecutor(max_workers=MAX_RUNS_AT_ONCE, thread_name_prefix="run")
        self.plan_pool = ThreadPoolExecutor(
            max_workers=MAX_PLANS_AT_ONCE, thread_name_prefix="plan"
        )
        self._running: set[str] = set()
        self._planning: set[str] = set()
        self._lock = threading.Lock()
        # One stop flag per job under way, keyed by its id; the loops read it before every
        # model call and every tool call, and it is gone once the job has ended.
        self._stops: dict[str, threading.Event] = {}

    # -- wiring ----------------------------------------------------------------------------

    def _default_chat(self, model: str) -> Chat:
        return OpenAIChat(self.settings.base_url, model, self.settings.api_key)

    def _default_runner(self) -> Runner:
        from provette.sandbox import make_runner

        return make_runner(self.settings.runner)

    @property
    def enabled(self) -> bool:
        return self.settings.live_enabled

    def runs_dir(self) -> Path:
        return self.settings.data_dir / "runs"

    def ref(self, run_id: str) -> EpisodeRef | None:
        if not run_id.isalnum():
            return None
        path = self.runs_dir() / run_id
        return (
            EpisodeRef("runs", "live", run_id, path) if (path / "request.json").is_file() else None
        )

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "model": self.model,
            "model_label": self.gallery.summary_label(self.model),
            "runner": self.settings.runner,
            "runner_label": runner_label(self.settings.runner),
            "cap_usd": self.settings.daily_cap_usd,
            "spent_today_usd": self.ledger.spent_today(),
            "remaining_usd": self.ledger.remaining(),
            "running": len(self._running),
            "planning": len(self._planning),
            "examples": [
                {"id": r["id"], "technique": r.get("technique"), "request": r["request"]}
                for r in self.gallery.requests.values()
            ],
        }

    # -- planning --------------------------------------------------------------------------

    def plan(self, request_text: str) -> dict[str, Any]:
        if not self.ledger.allows(PLAN_ESTIMATE_USD):
            raise HTTPException(503, self._cap_sentence())
        tuning = self.run_settings.values()
        result = plan(
            request_text,
            self.model,
            self.settings.base_url,
            self.settings.api_key,
            request_id="planned",
            chat=self.chat_factory(self.model),
            max_tool_calls=tuning["plan_tool_calls"],
            max_completion_tokens=tuning["plan_tokens"],
        )
        cost = self.gallery.prices.cost_usd(self.model, result.tokens_in, result.tokens_out)
        self.ledger.add(cost or 0.0)
        return {
            "platemap": dump_platemap(result.platemap) if result.platemap is not None else None,
            "error": result.error,
            "stop_reason": result.stop_reason,
            "tool_calls": result.tool_calls,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "cost_usd": cost,
            "seconds": result.seconds,
            "rejections": result.rejections,
            "steps": steps_from_transcript(
                [
                    {
                        **t,
                        "assistant": {
                            "content": t.get("content"),
                            "reasoning": t.get("reasoning"),
                            "tool_calls": t.get("tool_calls", []),
                        },
                    }
                    for t in result.transcript
                ]
            ),  # fmt: skip
        }

    def plans_dir(self) -> Path:
        return self.settings.data_dir / "plans"

    def plan_ref(self, plan_id: str) -> Path | None:
        path = self.plans_dir() / plan_id
        return path if plan_id.isalnum() and (path / "request.json").is_file() else None

    def start_plan(self, request_text: str, technique: str | None, *, anyway: bool = False) -> str:
        """The same planning as `plan`, in the pool, its turns written as they happen."""
        if not self.ledger.allows(PLAN_ESTIMATE_USD):
            raise HTTPException(503, self._cap_sentence())
        plan_id = secrets.token_urlsafe(9).replace("-", "a").replace("_", "b")
        with self._lock:
            if len(self._planning) >= MAX_PLANS_AT_ONCE:
                raise HTTPException(
                    503,
                    f"{MAX_PLANS_AT_ONCE} plans are being written already; try again in a minute.",
                )
            self._planning.add(plan_id)
        folder = self.plans_dir() / plan_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "request.json").write_text(
            json.dumps(
                {
                    "id": plan_id,
                    "request": request_text,
                    "technique": technique,
                    "created": time.time(),
                }
            ),
            encoding="utf-8",
        )
        _write_json(folder / "status.json", {"state": "running"})
        stop = threading.Event()
        with self._lock:
            self._stops[plan_id] = stop
        self.plan_pool.submit(
            self._plan_job, plan_id, request_text, technique, folder, stop, anyway
        )
        return plan_id

    def stop(self, job_id: str) -> str:
        """Ask a plan or a run under way to stop; it does so before its next model call or
        tool call and its record then says "stopped". Returns the job's state now."""
        with self._lock:
            event = self._stops.get(job_id)
        if event is None:
            raise HTTPException(409, "This one has already ended; there is nothing to stop.")
        event.set()
        return "stopping"

    def delete(self, folder: Path, job_id: str) -> None:
        """Remove a plan's or a run's record from this deployment, from the history for everyone.
        A job still under way is refused: stop it first, so no thread writes into a folder that
        is gone."""
        with self._lock:
            running = job_id in self._stops
        if running:
            raise HTTPException(409, "This one is still going. Stop it first, then delete it.")
        shutil.rmtree(folder, ignore_errors=True)

    def _forget_stop(self, job_id: str) -> None:
        with self._lock:
            self._stops.pop(job_id, None)

    def _plan_job(
        self,
        plan_id: str,
        request_text: str,
        technique: str | None,
        folder: Path,
        stop: threading.Event,
        anyway: bool = False,
    ) -> None:
        status: dict[str, Any] = {"state": "done"}
        tuning = self.run_settings.values()
        try:
            chat = RecordingChat(self.chat_factory(self.model), folder)
            result = plan(
                request_text,
                self.model,
                self.settings.base_url,
                self.settings.api_key,
                request_id="planned",
                technique=technique or None,
                chat=chat,
                should_stop=stop.is_set,
                allow_decline=not anyway,
                max_tool_calls=tuning["plan_tool_calls"],
                max_completion_tokens=tuning["plan_tokens"],
            )
            cost = self.gallery.prices.cost_usd(self.model, result.tokens_in, result.tokens_out)
            self.ledger.add(cost or 0.0)  # what was used is charged, stopped or not
            if result.stop_reason == STOPPED_BY_USER:
                status = {"state": "stopped"}
            _write_json(
                folder / "result.json",
                {
                    "platemap": dump_platemap(result.platemap)
                    if result.platemap is not None
                    else None,
                    "error": result.error,
                    "stop_reason": result.stop_reason,
                    "tool_calls": result.tool_calls,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "cost_usd": cost,
                    "seconds": result.seconds,
                    "rejections": result.rejections,
                    "declined": result.declined,
                },
            )
        except Exception as error:  # noqa: BLE001 - the page must say it, not hang
            log.exception("a live episode failed in %s", folder)
            status = {"state": "failed", "error": f"The run stopped: {error}"[:500]}
        finally:
            self._forget_stop(plan_id)
            with self._lock:
                self._planning.discard(plan_id)
            _write_json(folder / "status.json", status)

    def plan_snapshot(self, folder: Path) -> dict[str, Any]:
        """The planning so far: the request, the steps, thinking or not, and the result once
        there is one (the map, the cost, why it stopped)."""
        request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        status_path = folder / "status.json"
        status = (
            json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {}
        )
        transcript = folder / "transcript.jsonl"
        turns = (
            [
                json.loads(line)
                for line in transcript.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if transcript.is_file()
            else []
        )
        result_path = folder / "result.json"
        result = (
            json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
        )
        calls_so_far = sum(len((t.get("assistant") or {}).get("tool_calls") or []) for t in turns)
        tokens_in = sum(int((t.get("usage") or {}).get("prompt_tokens") or 0) for t in turns)
        tokens_out = sum(int((t.get("usage") or {}).get("completion_tokens") or 0) for t in turns)
        state = status.get("state", "running")
        return {
            "id": request["id"],
            "request": request["request"],
            "technique": request.get("technique"),
            "created": request.get("created"),
            "model": self.model,
            "model_label": self.gallery.summary_label(self.model),
            "state": state,
            "error": status.get("error") or result.get("error"),
            "thinking": state == "running" and _last_event_is_thinking(folder / "events.jsonl"),
            "steps": steps_from_transcript(turns),
            "platemap": result.get("platemap"),
            "stop_reason": result.get("stop_reason"),
            "rejections": result.get("rejections") or [],
            "declined": result.get("declined"),
            "tool_calls": result.get("tool_calls", calls_so_far),
            "tokens_in": result.get("tokens_in", tokens_in),
            "tokens_out": result.get("tokens_out", tokens_out),
            "cost_usd": result.get(
                "cost_usd", self.gallery.prices.cost_usd(self.model, tokens_in, tokens_out)
            ),
            "seconds": result.get("seconds"),
        }

    async def plan_events(
        self, folder: Path, poll_s: float = 0.5, max_s: float = 600
    ) -> AsyncIterator[str]:
        """Server-sent events, async so an open page holds no pool thread."""
        started = time.time()
        last_sig: tuple[Any, ...] | None = None
        while time.time() - started < max_s:
            sig = tuple(
                (folder / name).stat().st_size if (folder / name).is_file() else -1
                for name in ("transcript.jsonl", "events.jsonl", "result.json", "status.json")
            )
            if sig != last_sig:
                last_sig = sig
                snap = self.plan_snapshot(folder)
                yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                if snap["state"] in ENDED:
                    yield f"event: done\ndata: {json.dumps({'state': snap['state']})}\n\n"
                    return
            else:
                yield ": keep-alive\n\n"
            await anyio.sleep(poll_s)
        yield 'event: done\ndata: {"state": "timeout"}\n\n'

    def list_plans(self) -> list[dict[str, Any]]:
        """Every planning job on this deployment, newest first, one small row each: the
        request, its state and its outcome (planning · proposed · no map · failed · stopped),
        at most `LIST_AT_MOST`."""
        folder = self.plans_dir()
        if not folder.is_dir():
            return []
        rows = []
        for path in folder.iterdir():
            if self.plan_ref(path.name) is None:
                continue
            request = json.loads((path / "request.json").read_text(encoding="utf-8"))
            status_path = path / "status.json"
            status = (
                json.loads(status_path.read_text(encoding="utf-8")) if status_path.is_file() else {}
            )
            result_path = path / "result.json"
            result = (
                json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
            )
            state = status.get("state", "running")
            rows.append(
                {
                    "id": request["id"],
                    "request": request["request"],
                    "technique": request.get("technique"),
                    "created": request.get("created"),
                    "state": state,
                    "outcome": _plan_outcome(state, result),
                    "tool_calls": result.get("tool_calls"),
                    "cost_usd": result.get("cost_usd"),
                }
            )
        rows.sort(key=lambda r: r.get("created") or 0, reverse=True)
        return rows[:LIST_AT_MOST]

    def list_runs(self) -> list[dict[str, Any]]:
        """Every live run on this deployment, newest first: finished ones as gallery cards,
        the rest with their state."""
        folder = self.runs_dir()
        if not folder.is_dir():
            return []
        rows = []
        for path in folder.iterdir():
            ref = self.ref(path.name)
            if ref is None:
                continue
            request = self.gallery.request_of(ref)
            state = self.state(ref).get("state", "running")
            if (ref.path / "done.json").is_file():
                row = dict(self.gallery.summary(ref))
            else:
                row = {
                    "id": ref.id,
                    "set": "runs",
                    "current": False,
                    "run_label": "live",
                    "condition": "plain",
                    "condition_label": "the request as written",
                    "request_id": ref.request_id,
                    "technique": request.get("technique"),
                    "request": request.get("request", ""),
                    "model": self.model,
                    "model_label": self.gallery.summary_label(self.model),
                    "runner": self.settings.runner,
                    "runner_label": runner_label(self.settings.runner),
                    "candidates": None,
                    "verified": False,
                    "outcome": None,
                    "drafts": None,
                    "tool_calls": None,
                    "tokens_in": None,
                    "tokens_out": None,
                    "cost_usd": None,
                    "seconds": None,
                    "stop_reason": None,
                }
            row.update(_live_words(request))
            row["run_id"] = ref.request_id
            row["state"] = state
            row["created"] = request.get("created")
            rows.append(row)
        rows.sort(key=lambda r: r.get("created") or 0, reverse=True)
        return rows[:LIST_AT_MOST]

    def _cap_sentence(self) -> str:
        return (
            f"The live flow is paused for today: ${self.ledger.spent_today():.2f} of the "
            f"${self.settings.daily_cap_usd:.2f} daily budget is spent. The gallery and the "
            "checker still work; the flow comes back tomorrow (UTC)."
        )

    # -- running ---------------------------------------------------------------------------

    def start(
        self, request_text: str, platemap: dict[str, Any], technique: str | None = None
    ) -> str:
        if not self.ledger.allows(RUN_ESTIMATE_USD):
            raise HTTPException(503, self._cap_sentence())
        with self._lock:
            if len(self._running) >= MAX_RUNS_AT_ONCE:
                raise HTTPException(
                    503, f"{MAX_RUNS_AT_ONCE} episodes are running already; try again in a minute."
                )
            run_id = secrets.token_urlsafe(9).replace("-", "a").replace("_", "b")
            self._running.add(run_id)
        folder = self.runs_dir() / run_id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "request.json").write_text(
            json.dumps(
                {
                    "id": run_id,
                    "request": request_text,
                    "technique": technique or None,
                    "created": time.time(),
                }
            ),  # fmt: skip
            encoding="utf-8",
        )
        (folder / "platemap.json").write_text(json.dumps(platemap, indent=1), encoding="utf-8")
        _write_json(folder / "status.json", {"state": "running"})
        stop = threading.Event()
        with self._lock:
            self._stops[run_id] = stop
        self.pool.submit(self._run, run_id, request_text, folder, stop)
        return run_id

    def _run(self, run_id: str, request_text: str, folder: Path, stop: threading.Event) -> None:
        status: dict[str, Any] = {"state": "done"}
        runner = self.runner_factory()
        tuning = self.run_settings.values()
        try:
            chat = EventChat(self.chat_factory(self.model), folder / "events.jsonl")
            done = run_episode(
                {"id": run_id, "request": request_text},
                folder / "platemap.json",
                runner,
                self.model,
                self.settings.base_url,
                self.settings.api_key,
                folder,
                "plain",
                chat=chat,
                should_stop=stop.is_set,
                min_drafts=tuning["run_min_drafts"],
                max_tool_calls=tuning["run_tool_calls"],
                max_completion_tokens=tuning["run_tokens"],
            )
            cost = self.gallery.prices.cost_usd(
                self.model, int(done.get("tokens_in") or 0), int(done.get("tokens_out") or 0)
            )
            self.ledger.add(cost or 0.0)  # what was used is charged, stopped or not
            if done.get("stop_reason") == STOPPED_BY_USER:
                status = {"state": "stopped"}
        except Exception as error:  # noqa: BLE001 - the page must say it, not hang
            log.exception("a live episode failed in %s", folder)
            status = {"state": "failed", "error": f"The run stopped: {error}"[:500]}
        finally:
            runner.close()
            self._forget_stop(run_id)
            with self._lock:
                self._running.discard(run_id)
            _write_json(folder / "status.json", status)

    # -- reading ---------------------------------------------------------------------------

    def state(self, ref: EpisodeRef) -> dict[str, Any]:
        path = ref.path / "status.json"
        row: dict[str, Any] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        return row or {"state": "running"}

    def thinking(self, ref: EpisodeRef) -> bool:
        return _last_event_is_thinking(ref.path / "events.jsonl")

    def snapshot(self, ref: EpisodeRef) -> dict[str, Any]:
        """The run so far: the gallery's detail (steps, drafts, verdict when there is one)."""
        state = self.state(ref)
        done_path = ref.path / "done.json"
        if done_path.is_file():
            row = self.gallery.detail(ref)
        else:
            transcript = self.gallery.files_dir(ref) / "transcript.jsonl"
            turns = []
            if transcript.is_file():
                turns = [
                    json.loads(line)
                    for line in transcript.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            request = self.gallery.request_of(ref)
            row = {
                "id": ref.id,
                "request_id": ref.request_id,
                "request": request.get("request", ""),
                "technique": request.get("technique"),
                "model": self.model,
                "model_label": self.gallery.summary_label(self.model),
                "runner": self.settings.runner,
                "runner_label": runner_label(self.settings.runner),
                "candidates": None,
                "condition": "plain",
                "condition_label": "the request as written",
                "verified": False,
                "outcome": None,
                "platemap": self.gallery.platemap_for(ref),
                "steps": steps_from_transcript(turns),
                "draft_rows": self.gallery.drafts(ref),
                "final_draft": None,
                "cost_usd": None,
                "seconds": None,
                "tokens_in": sum(
                    int((t.get("usage") or {}).get("prompt_tokens") or 0) for t in turns
                ),
                "tokens_out": sum(
                    int((t.get("usage") or {}).get("completion_tokens") or 0) for t in turns
                ),
                "prices_read_on": self.gallery.prices.read_on,
            }
            row["cost_usd"] = self.gallery.prices.cost_usd(
                self.model, row["tokens_in"], row["tokens_out"]
            )
        request = self.gallery.request_of(ref)
        row.update(_live_words(request))
        row["state"] = state.get("state")
        row["error"] = state.get("error")
        row["created"] = request.get("created")
        row["thinking"] = state.get("state") == "running" and self.thinking(ref)
        return row

    async def events(
        self, ref: EpisodeRef, poll_s: float = 0.5, max_s: float = 3600
    ) -> AsyncIterator[str]:
        """Server-sent events: a `snapshot` whenever the run's files change, then `done`. Async,
        so forty open tabs hold no pool threads; it ends when status.json says the run is
        over, and at `max_s` at the latest."""
        started = time.time()
        last_sig: tuple[Any, ...] | None = None
        while time.time() - started < max_s:
            transcript = ref.path / "transcript.jsonl"
            events = ref.path / "events.jsonl"
            sig = (
                transcript.stat().st_size if transcript.is_file() else -1,
                events.stat().st_size if events.is_file() else -1,
                (ref.path / "done.json").is_file(),
                (ref.path / "status.json").stat().st_mtime
                if (ref.path / "status.json").is_file()
                else 0,
            )
            if sig != last_sig:
                last_sig = sig
                snap = self.snapshot(ref)
                yield f"event: snapshot\ndata: {json.dumps(snap)}\n\n"
                if snap["state"] in ENDED:
                    yield f"event: done\ndata: {json.dumps({'state': snap['state']})}\n\n"
                    return
            else:
                yield ": keep-alive\n\n"
            await anyio.sleep(poll_s)
        yield 'event: done\ndata: {"state": "timeout"}\n\n'


def _plan_outcome(state: str, result: dict[str, Any]) -> str:
    """One word for the history's row: planning · proposed · not a request · no map · failed ·
    stopped."""
    if state == "running":
        return "planning"
    if state == "failed":
        return "failed"
    if state == "stopped":
        return "stopped"
    if result.get("platemap"):
        return "proposed"
    return "not a request" if result.get("declined") else "no map"


def _live_words(request: dict[str, Any]) -> dict[str, Any]:
    """What a live run's card and header say in place of the evaluation's set words."""
    return {
        "set": "runs",
        "current": False,
        "run_label": "live, on this deployment",
        "condition": "plain",
        "condition_label": "the request as written",
        "technique": request.get("technique") or "Your request",
    }


def _write_json(path: Path, row: dict[str, Any]) -> None:
    """Written whole then renamed into place, so a poller never reads a half-written record."""
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(row), encoding="utf-8")
    tmp.replace(path)


def _last_event_is_thinking(path: Path) -> bool:
    if not path.is_file():
        return False
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line
    return bool(last) and json.loads(last).get("type") == "thinking"


# ---------------------------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------------------------


def _live(request: Request) -> Live:
    live: Live = request.app.state.live
    return live


def _require_password(request: Request, live: Live) -> None:
    if not live.enabled:
        raise HTTPException(
            503,
            "The live flow is off on this deployment: it needs a Token Factory key and a judge "
            "password. The gallery and the checker work without them.",
        )
    require_judge_password(request, "the live flow")


def _ref(request: Request, run_id: str) -> EpisodeRef:
    ref = _live(request).ref(run_id)
    if ref is None:
        raise HTTPException(404, "no such run")
    return ref


def _platemap(row: dict[str, Any]) -> dict[str, Any]:
    try:
        platemap_from_dict(row)
    except PlateMapError as error:
        raise HTTPException(422, f"the plate map is not valid: {error}") from error
    return row


@router.get("/live")
def live_status(request: Request) -> dict[str, Any]:
    return _live(request).status()


@router.post("/plan")
def plan_route(request: Request, body: PlanRequest) -> dict[str, Any]:
    live = _live(request)
    _require_password(request, live)
    plan_limit.guard(request, "plans")
    return live.plan(body.request.strip())


@router.post("/plans")
def start_plan(request: Request, body: PlanRequest) -> dict[str, Any]:
    live = _live(request)
    _require_password(request, live)
    text = body.request.strip()
    if not body.anyway and not looks_like_lab_request(text):
        raise HTTPException(422, {"code": "not_a_request", "message": NOT_A_REQUEST_WORDS})
    plan_limit.guard(request, "plans")
    technique = (body.technique or "").strip() or None
    return {"id": live.start_plan(text, technique, anyway=body.anyway)}


@router.get("/plans")
def list_plans(request: Request) -> dict[str, Any]:
    return {"plans": _live(request).list_plans()}


def _plan_folder(request: Request, plan_id: str) -> Path:
    folder = _live(request).plan_ref(plan_id)
    if folder is None:
        raise HTTPException(404, "no such plan")
    return folder


@router.get("/plans/{plan_id}")
def get_plan(request: Request, plan_id: str) -> dict[str, Any]:
    return _live(request).plan_snapshot(_plan_folder(request, plan_id))


@router.get("/plans/{plan_id}/events")
def plan_events(request: Request, plan_id: str) -> StreamingResponse:
    live = _live(request)
    folder = _plan_folder(request, plan_id)
    return StreamingResponse(
        live.plan_events(folder),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/plans/{plan_id}/stop")
def stop_plan(request: Request, plan_id: str) -> dict[str, Any]:
    live = _live(request)
    _require_password(request, live)
    _plan_folder(request, plan_id)
    return {"id": plan_id, "state": live.stop(plan_id)}


@router.delete("/plans/{plan_id}")
def delete_plan(request: Request, plan_id: str) -> dict[str, Any]:
    require_judge_password(request, "deleting")
    _live(request).delete(_plan_folder(request, plan_id), plan_id)
    return {"id": plan_id, "deleted": True}


@router.delete("/runs/{run_id}")
def delete_run(request: Request, run_id: str) -> dict[str, Any]:
    require_judge_password(request, "deleting")
    _live(request).delete(_ref(request, run_id).path, run_id)
    return {"id": run_id, "deleted": True}


@router.get("/runs")
def list_runs(request: Request) -> dict[str, Any]:
    return {"runs": _live(request).list_runs()}


@router.post("/runs")
def start_run(request: Request, body: RunRequest) -> dict[str, Any]:
    live = _live(request)
    _require_password(request, live)
    run_limit.guard(request, "runs")
    platemap = _platemap(body.platemap)
    technique = (body.technique or "").strip() or None
    run_id = live.start(body.request.strip(), platemap, technique)
    return {"id": run_id, "by": client_key(request)}


@router.get("/runs/{run_id}")
def get_run(request: Request, run_id: str) -> dict[str, Any]:
    return _live(request).snapshot(_ref(request, run_id))


@router.get("/runs/{run_id}/events")
def run_events(request: Request, run_id: str) -> StreamingResponse:
    live = _live(request)
    ref = _ref(request, run_id)
    return StreamingResponse(
        live.events(ref),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/stop")
def stop_run(request: Request, run_id: str) -> dict[str, Any]:
    live = _live(request)
    _require_password(request, live)
    _ref(request, run_id)
    return {"id": run_id, "state": live.stop(run_id)}


@router.get("/runs/{run_id}/drafts/{n}")
def run_draft(request: Request, run_id: str, n: int) -> dict[str, Any]:
    live = _live(request)
    row = live.gallery.draft(_ref(request, run_id), n)
    if row is None:
        raise HTTPException(404, "no such draft")
    return row


@router.get("/runs/{run_id}/analysis")
def run_analysis(request: Request, run_id: str) -> dict[str, Any]:
    live = _live(request)
    try:
        row = live.gallery.analysis(_ref(request, run_id))
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error
    if row is None:
        raise HTTPException(404, "this run has no draft to analyse")
    return row


@router.get("/runs/{run_id}/protocol.py", response_class=PlainTextResponse)
def run_protocol(request: Request, run_id: str) -> str:
    final = _live(request).gallery.final_draft(_ref(request, run_id))
    if final is None:
        raise HTTPException(404, "this run has no draft")
    return str(final["text"])


@router.get("/runs/{run_id}/replay.html", response_class=HTMLResponse)
def run_replay(
    request: Request,
    run_id: str,
    theme: str | None = None,
    embed: bool = False,
    compact: bool = False,
) -> str:
    live = _live(request)
    try:
        row = live.gallery.analysis(_ref(request, run_id))
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error
    if row is None or not row.get("replay"):
        raise HTTPException(
            404, "the final draft did not pass the simulator, so there is no replay"
        )
    return replay_page(row["replay"], theme, embed, compact)
