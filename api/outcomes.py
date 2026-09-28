"""The failed-run record: after a run, "did this run work?", and two sentences when it did not.

    POST /api/outcomes   {"episode": "<set>/<condition>/<id>", "ok": bool, "note": str}   (password)
    GET  /api/outcomes                       every record, newest first, and the failures
    GET  /api/outcomes?episode=<id>          the latest record for one episode

One JSON row per record in <data_dir>/outcomes.jsonl: episode, set, when, ok, note. The rules
page lists the "no" records as failures without a rule yet: the seed of a rule, not a ticket.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import require_judge_password
from api.episodes import Gallery
from api.settings import Settings

router = APIRouter(prefix="/api", tags=["outcomes"])

MAX_NOTE = 600


class OutcomeIn(BaseModel):
    episode: str = Field(..., min_length=3, max_length=200)
    ok: bool
    note: str = Field("", max_length=MAX_NOTE)


def _path(cfg: Settings) -> Path:
    return cfg.data_dir / "outcomes.jsonl"


def read_all(cfg: Settings) -> list[dict[str, Any]]:
    path = _path(cfg)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _episode_ref(request: Request, episode_id: str) -> tuple[str, dict[str, Any] | None]:
    """The set the episode belongs to, and its card when the gallery (or a live run) has it."""
    gallery: Gallery = request.app.state.gallery
    ref = gallery.ref(episode_id)
    if ref is None:
        live = getattr(request.app.state, "live", None)
        run_id = episode_id.rsplit("/", 1)[-1]
        ref = live.ref(run_id) if live is not None else None
    if ref is None:
        return episode_id.split("/")[0], None
    return ref.set_name, gallery.summary(ref)


@router.post("/outcomes")
def record_outcome(request: Request, body: OutcomeIn) -> dict[str, Any]:
    require_judge_password(request, "recording an outcome")
    cfg: Settings = request.app.state.settings
    if not body.ok and not body.note.strip():
        raise HTTPException(422, "Say what went wrong, and in which wells: a sentence or two.")
    set_name, card = _episode_ref(request, body.episode)
    if card is None:
        raise HTTPException(404, "no such episode")
    row = {
        "episode": body.episode,
        "set": set_name,
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": body.ok,
        "note": " ".join(body.note.split()),
    }
    path = _path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


@router.get("/outcomes")
def list_outcomes(request: Request, episode: str | None = None) -> dict[str, Any]:
    cfg: Settings = request.app.state.settings
    rows = read_all(cfg)
    if episode is not None:
        mine = [r for r in rows if r.get("episode") == episode]
        return {"episode": episode, "latest": mine[-1] if mine else None, "records": mine}
    gallery: Gallery = request.app.state.gallery
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        latest[str(r.get("episode"))] = r  # the last row for an episode is its current record
    failures = []
    for r in reversed(list(latest.values())):
        if r.get("ok"):
            continue
        ref = gallery.ref(str(r.get("episode")))
        card = gallery.summary(ref) if ref is not None else None
        failures.append(
            {
                **r,
                "request": card["request"] if card else None,
                "technique": card["technique"] if card else None,
                "model_label": card["model_label"] if card else None,
            }
        )
    return {"records": list(reversed(rows)), "failures": failures}
