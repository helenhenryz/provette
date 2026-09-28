"""Check a protocol you already have: paste or upload it, optionally with a plate map, and get
the report, the replay and the prep sheet. No model call.

    POST /api/checks                    {"protocol": str, "platemap": dict|str|null, "name": str}
    GET  /api/checks                    this deployment's checks, newest first, a small row each
    GET  /api/checks/{id}               the stored analysis (api.worker's dict) and the inputs
    GET  /api/checks/{id}/replay.html   `provette view`'s page
    GET  /api/checks/{id}/protocol.py   the protocol as it was checked
    GET  /api/platemaps                 the example plate maps (id, request) a visitor may pick
    GET  /api/platemaps/{id}            one of them
    GET  /api/examples/protocol         the reference protocol with planted bugs, to try

Every check is kept under <data_dir>/checks/<id>/ so its URL can be shared. Ids are random.
"""

from __future__ import annotations

import ast
import json
import re
import secrets
import shutil
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from api.analysis import AnalysisError, analyse
from api.auth import require_judge_password
from api.episodes import Gallery
from api.limits import RateLimit
from api.replay_page import replay_page
from api.settings import Settings
from provette.intent.spec import PlateMapError, platemap_from_dict

router = APIRouter(prefix="/api", tags=["checks"])

MAX_PROTOCOL_CHARS = 200_000
MAX_PLATEMAP_CHARS = 200_000
EXAMPLE_PLATEMAP = "pcr-01"
limit = RateLimit(n=20, per_s=60)


class CheckRequest(BaseModel):
    protocol: str = Field(..., description="the protocol's Python source")
    platemap: dict[str, Any] | str | None = Field(None, description="a plate map: JSON or text")
    name: str = Field("protocol.py", max_length=120)


def _settings(request: Request) -> Settings:
    cfg: Settings = request.app.state.settings
    return cfg


def _dir(cfg: Settings, check_id: str) -> Path:
    if not check_id.isalnum():
        raise HTTPException(404, "no such check")
    return cfg.data_dir / "checks" / check_id


def _read_platemap(raw: dict[str, Any] | str | None) -> dict[str, Any] | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        if len(raw) > MAX_PLATEMAP_CHARS:
            raise HTTPException(413, "the plate map is too large")
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as error:
            raise HTTPException(422, f"the plate map is not JSON: {error}") from error
    else:
        row = raw
    if not isinstance(row, dict):
        raise HTTPException(422, "the plate map must be a JSON object")
    try:
        platemap_from_dict(row)
    except PlateMapError as error:
        raise HTTPException(422, f"the plate map is not valid: {error}") from error
    return row


# every protocol the robot runs defines run(protocol); the whole public library does (833 of 833)
_RUN = re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+run[ \t]*\(", re.MULTILINE)


def protocol_problem(source: str) -> str | None:
    """Why this text is not an Opentrons protocol at all, or None when it may be one.

    Generous on purpose: anything with a `def run(` goes on to the simulator, even with a syntax
    error, because a protocol with a typo is still a protocol and the simulator's report names
    the line. Refused: a binary file, and Python (or anything else) with no run function.
    """
    if "\x00" in source:
        return "This is not a text file, so it cannot be a protocol."
    if _RUN.search(source):
        return None
    try:
        ast.parse(source)
    except SyntaxError:
        return (
            "This is not a Python protocol: it does not read as Python and has no "
            "run(protocol) function."
        )
    return (
        "This Python file is not an Opentrons protocol: it has no run(protocol) function, "
        "which every protocol the robot runs defines."
    )


@router.post("/checks")
def create_check(request: Request, body: CheckRequest) -> dict[str, Any]:
    limit.guard(request, "checks")
    cfg = _settings(request)
    if not body.protocol.strip():
        raise HTTPException(422, "the protocol is empty")
    if len(body.protocol) > MAX_PROTOCOL_CHARS:
        raise HTTPException(413, "the protocol is too large")
    problem = protocol_problem(body.protocol)
    if problem:
        raise HTTPException(422, problem)
    platemap = _read_platemap(body.platemap)
    try:
        analysis = analyse(
            body.protocol,
            platemap,
            cfg.cache_dir,
            roles_file=cfg.roles_file,
            sources_file=cfg.sources_file,
        )
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error
    check_id = secrets.token_urlsafe(9).replace("-", "a").replace("_", "b")
    folder = _dir(cfg, check_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "protocol.py").write_text(body.protocol, encoding="utf-8")
    if platemap is not None:
        (folder / "platemap.json").write_text(json.dumps(platemap, indent=1), encoding="utf-8")
    (folder / "analysis.json").write_text(
        json.dumps(analysis, separators=(",", ":")), encoding="utf-8"
    )
    meta = {"id": check_id, "name": _safe_name(body.name), "created": time.time()}
    (folder / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    # The small row the list serves, kept apart so listing fifty checks reads no analysis.
    (folder / "summary.json").write_text(
        json.dumps(_summary(meta, analysis, platemap is not None)), encoding="utf-8"
    )
    return _row(folder, meta, analysis, body.protocol, platemap)


LIST_AT_MOST = 50


def _summary(meta: dict[str, Any], analysis: dict[str, Any], has_map: bool) -> dict[str, Any]:
    """One line for the Runs page: what was checked, did the simulator pass, how many findings."""
    passed = bool((analysis.get("simulator") or {}).get("passed"))
    check = analysis.get("check") or {}
    return {
        "id": meta["id"],
        "name": meta["name"],
        "created": meta["created"],
        "simulator": "passed" if passed else "rejected",
        "findings": len(check.get("findings") or []) if passed else 0,
        "has_map": has_map,
    }


@router.get("/checks")
def list_checks(request: Request) -> dict[str, Any]:
    """This deployment's checks, newest first, at most `LIST_AT_MOST`. A check made before the
    summary file existed is summarised from its analysis on the way past."""
    folder = _settings(request).data_dir / "checks"
    rows: list[dict[str, Any]] = []
    if folder.is_dir():
        for path in folder.iterdir():
            if not (path / "meta.json").is_file() or not (path / "analysis.json").is_file():
                continue
            summary_path = path / "summary.json"
            if summary_path.is_file():
                rows.append(json.loads(summary_path.read_text(encoding="utf-8")))
                continue
            meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
            analysis = json.loads((path / "analysis.json").read_text(encoding="utf-8"))
            rows.append(_summary(meta, analysis, (path / "platemap.json").is_file()))
    rows.sort(key=lambda r: r.get("created") or 0, reverse=True)
    return {"checks": rows[:LIST_AT_MOST]}


def _safe_name(name: str) -> str:
    name = name.strip().replace("/", "_") or "protocol.py"
    return name if name.endswith(".py") else name + ".py"


def _row(
    folder: Path,
    meta: dict[str, Any],
    analysis: dict[str, Any],
    protocol: str,
    platemap: dict[str, Any] | None,
) -> dict[str, Any]:
    del folder
    return {**meta, "analysis": analysis, "protocol": protocol, "platemap": platemap}


def _load(cfg: Settings, check_id: str) -> tuple[Path, dict[str, Any]]:
    folder = _dir(cfg, check_id)
    if not (folder / "analysis.json").is_file():
        raise HTTPException(404, "no such check")
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    return folder, meta


@router.get("/checks/{check_id}")
def get_check(request: Request, check_id: str) -> dict[str, Any]:
    folder, meta = _load(_settings(request), check_id)
    analysis = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
    protocol = (folder / "protocol.py").read_text(encoding="utf-8")
    platemap_path = folder / "platemap.json"
    platemap = None
    if platemap_path.is_file():
        platemap = json.loads(platemap_path.read_text(encoding="utf-8"))
    return _row(folder, meta, analysis, protocol, platemap)


@router.delete("/checks/{check_id}")
def delete_check(request: Request, check_id: str) -> dict[str, Any]:
    """Remove a check from this deployment (and from everyone's history); the judge password,
    like every other write on a person's behalf."""
    require_judge_password(request, "deleting")
    folder = _dir(_settings(request), check_id)
    if not folder.is_dir():
        raise HTTPException(404, "no such check")
    shutil.rmtree(folder, ignore_errors=True)
    return {"id": check_id, "deleted": True}


@router.get("/checks/{check_id}/replay.html", response_class=HTMLResponse)
def check_replay(
    request: Request,
    check_id: str,
    theme: str | None = None,
    embed: bool = False,
    compact: bool = False,
) -> str:
    folder, _ = _load(_settings(request), check_id)
    analysis = json.loads((folder / "analysis.json").read_text(encoding="utf-8"))
    if not analysis.get("replay"):
        raise HTTPException(404, "the simulator rejected this protocol, so there is no replay")
    return replay_page(analysis["replay"], theme, embed, compact)


@router.get("/checks/{check_id}/protocol.py", response_class=PlainTextResponse)
def check_protocol(request: Request, check_id: str) -> str:
    folder, _ = _load(_settings(request), check_id)
    return (folder / "protocol.py").read_text(encoding="utf-8")


@router.get("/platemaps")
def platemaps(request: Request) -> dict[str, Any]:
    cfg = _settings(request)
    rows = []
    for _, folder in cfg.request_sets:
        for path in sorted(folder.glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            if "variants" not in row:
                continue  # not a plate map (eval/requests-hard holds other JSON too, maybe)
            rows.append({"id": row.get("id", path.stem), "request": row.get("request", "")})
    return {"platemaps": rows}


@router.get("/platemaps/{platemap_id}")
def platemap(request: Request, platemap_id: str) -> dict[str, Any]:
    gallery: Gallery = request.app.state.gallery
    row = gallery.platemap(platemap_id)
    if row is None:
        raise HTTPException(404, "no such plate map")
    return row


@router.get("/examples/protocol")
def example_protocol(request: Request) -> dict[str, Any]:
    """The protocol the check page offers to try: `tests/fixtures/protocols/pcr_buggy.py` in a
    checkout, `PROVETTE_EXAMPLE_PROTOCOL` in the image (the tests are not in it; measured
    the route answered 500 there before the setting existed)."""
    path = _settings(request).example_protocol
    if not path.is_file():
        raise HTTPException(404, f"the example protocol is not on this deployment ({path})")
    return {
        "name": path.name,
        "protocol": path.read_text(encoding="utf-8"),
        "platemap_id": EXAMPLE_PLATEMAP,
        "about": (
            "The reference protocol from the test suite: a PCR set-up with bugs planted on "
            "purpose. The simulator passes it; the checks do not."
        ),
    }
