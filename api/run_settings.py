"""The settings a person may change from the page: the budgets of a live run and of a plan.

    GET    /api/run-settings   every setting: its value, its default, its range, its words
    PUT    /api/run-settings   {"key": value, ...}; the judge key; out of range is refused
    DELETE /api/run-settings   back to the defaults; the judge key

The defaults are the constants the code already runs with (`provette.agent.loop`,
`provette.planner.loop`), so a deployment nobody touched runs as
before. A change is kept in `<data_dir>/run-settings.json` and holds for everyone on this
deployment from the next plan or run; the jobs read `RunSettings.values()` when they start.

Not here on purpose: the day's spend cap and the rate limits. They protect the account that
pays, so they stay in the deployment's environment (`api/settings.py`). Every ceiling below
keeps one run's cost within what the cap expects.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.auth import require_judge_password
from provette.agent import loop as agent_loop
from provette.planner import loop as planner_loop

LIVE_MIN_DRAFTS = agent_loop.MIN_DRAFTS  # D-32: the product and the evaluation alike


@dataclass(frozen=True)
class Setting:
    key: str
    group: str
    label: str
    words: str
    default: int
    low: int
    high: int


SETTINGS: tuple[Setting, ...] = (
    Setting(
        "run_tool_calls",
        "Runs",
        "Tool calls per run",
        "The run stops after this many tool calls (writing a draft, a check, a calculator).",
        agent_loop.MAX_TOOL_CALLS,
        5,
        60,
    ),
    Setting(
        "run_tokens",
        "Runs",
        "Tokens per run",
        "The model's output across the run, reasoning included; past it the run stops "
        "with a token budget.",
        agent_loop.MAX_COMPLETION_TOKENS,
        20000,
        200000,
    ),
    Setting(
        "run_min_drafts",
        "Runs",
        "Drafts before giving up",
        "A draft the checks reject is not accepted as the answer until this many were written.",
        LIVE_MIN_DRAFTS,
        0,
        6,
    ),
    Setting(
        "plan_tool_calls",
        "Plans",
        "Tool calls per plan",
        "The planner stops after this many tool calls without a plate map.",
        planner_loop.MAX_TOOL_CALLS,
        3,
        30,
    ),
    Setting(
        "plan_tokens",
        "Plans",
        "Tokens per plan",
        "The planner's output, reasoning included; past it the plan stops with no map.",
        planner_loop.MAX_COMPLETION_TOKENS,
        10000,
        100000,
    ),
)
BY_KEY = {s.key: s for s in SETTINGS}
DEFAULTS = {s.key: s.default for s in SETTINGS}


class RunSettings:
    """The saved changes over the defaults. A missing or broken file is the defaults."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def values(self) -> dict[str, int]:
        saved: dict[str, Any] = {}
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        out = dict(DEFAULTS)
        for key, value in (saved if isinstance(saved, dict) else {}).items():
            setting = BY_KEY.get(key)
            if setting and isinstance(value, int) and setting.low <= value <= setting.high:
                out[key] = value
        return out

    def update(self, changes: dict[str, Any]) -> dict[str, int]:
        """Apply `changes`; any unknown key or value out of range refuses the whole change."""
        for key, value in changes.items():
            setting = BY_KEY.get(key)
            if setting is None:
                raise HTTPException(422, f"there is no setting named {key!r}")
            if isinstance(value, bool) or not isinstance(value, int):
                raise HTTPException(422, f"{setting.label}: a whole number, please")
            if not setting.low <= value <= setting.high:
                raise HTTPException(
                    422, f"{setting.label}: between {setting.low:,} and {setting.high:,}"
                )
        with self._lock:
            merged = {**self.values(), **changes}
            kept = {k: v for k, v in merged.items() if v != DEFAULTS[k]}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(kept, indent=1), encoding="utf-8")
        return self.values()

    def reset(self) -> dict[str, int]:
        with self._lock:
            self.path.unlink(missing_ok=True)
        return self.values()


def describe(values: dict[str, int]) -> dict[str, Any]:
    return {
        "settings": [
            {
                "key": s.key,
                "group": s.group,
                "label": s.label,
                "words": s.words,
                "value": values[s.key],
                "default": s.default,
                "low": s.low,
                "high": s.high,
            }
            for s in SETTINGS
        ]
    }


router = APIRouter(prefix="/api", tags=["settings"])


def _store(request: Request) -> RunSettings:
    store: RunSettings = request.app.state.run_settings
    return store


@router.get("/run-settings")
def get_settings(request: Request) -> dict[str, Any]:
    return describe(_store(request).values())


@router.put("/run-settings")
def put_settings(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    require_judge_password(request, "changing the settings")
    return describe(_store(request).update(body))


@router.delete("/run-settings")
def reset_settings(request: Request) -> dict[str, Any]:
    require_judge_password(request, "changing the settings")
    return describe(_store(request).reset())
