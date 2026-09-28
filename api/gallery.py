"""The gallery's routes: the pre-run episodes, read-only, no key needed.

GET /api/episodes                                   the cards
GET /api/episodes/{set}/{condition}/{id}            the story (steps, drafts, plate map)
GET /api/episodes/{set}/{condition}/{id}/drafts/{n} one draft's text and its checks
GET /api/episodes/{set}/{condition}/{id}/analysis   check, verify and the replay export
GET /api/episodes/{set}/{condition}/{id}/protocol.py  the final draft, to download
GET /api/episodes/{set}/{condition}/{id}/replay.html  `provette view`'s page for the final draft
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from api.analysis import AnalysisError
from api.episodes import EpisodeRef, Gallery
from api.replay_page import replay_page

router = APIRouter(prefix="/api/episodes", tags=["gallery"])


def _gallery(request: Request) -> Gallery:
    gallery: Gallery = request.app.state.gallery
    return gallery


def _ref(request: Request, set_name: str, condition: str, request_id: str) -> EpisodeRef:
    ref = _gallery(request).ref(f"{set_name}/{condition}/{request_id}")
    if ref is None:
        raise HTTPException(404, "no such episode")
    return ref


@router.get("")
def list_episodes(request: Request) -> dict[str, Any]:
    gallery = _gallery(request)
    return {
        "episodes": gallery.list(),
        "sets": list(gallery.settings.gallery_sets),
        "prices_read_on": gallery.prices.read_on,
    }


@router.get("/{set_name}/{condition}/{request_id}")
def episode(request: Request, set_name: str, condition: str, request_id: str) -> dict[str, Any]:
    return _gallery(request).detail(_ref(request, set_name, condition, request_id))


@router.get("/{set_name}/{condition}/{request_id}/drafts/{n}")
def draft(
    request: Request, set_name: str, condition: str, request_id: str, n: int
) -> dict[str, Any]:
    row = _gallery(request).draft(_ref(request, set_name, condition, request_id), n)
    if row is None:
        raise HTTPException(404, "no such draft")
    return row


@router.get("/{set_name}/{condition}/{request_id}/analysis")
def analysis(request: Request, set_name: str, condition: str, request_id: str) -> dict[str, Any]:
    try:
        row = _gallery(request).analysis(_ref(request, set_name, condition, request_id))
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error
    if row is None:
        raise HTTPException(404, "this episode has no draft to analyse")
    return row


@router.get("/{set_name}/{condition}/{request_id}/protocol.py", response_class=PlainTextResponse)
def protocol(request: Request, set_name: str, condition: str, request_id: str) -> str:
    final = _gallery(request).final_draft(_ref(request, set_name, condition, request_id))
    if final is None:
        raise HTTPException(404, "this episode has no draft")
    return str(final["text"])


@router.get("/{set_name}/{condition}/{request_id}/replay.html", response_class=HTMLResponse)
def replay_html(
    request: Request,
    set_name: str,
    condition: str,
    request_id: str,
    theme: str | None = None,
    embed: bool = False,
    compact: bool = False,
) -> str:
    try:
        row = _gallery(request).analysis(_ref(request, set_name, condition, request_id))
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error
    if row is None or not row.get("replay"):
        raise HTTPException(
            404, "the final draft did not pass the simulator, so there is no replay"
        )
    return replay_page(row["replay"], theme, embed, compact)
