"""Declared rules: the YAML rules written through the form (provette/rules/declared.py).

    GET  /api/rules/sources              the sources a rule may rest on
                                         (provette/rules/sources.yaml, read on each call), with
                                         the three shapes
    POST /api/rules/sources              {"key", "name", "url"} -> appends the source to that
                                         file and reloads (judge password)
    GET  /api/rules/declared             every declared rule file, as data, with its status
    POST /api/rules/preview              {"rule": data, "episode": id} -> the findings the rule
                                         would raise on that episode's final draft (no save)
    POST /api/rules/declared             {"rule": data} -> validate, save as proposed, reload RULES
                                         (judge password)

The engine does the work: `declared.validate` (an error names the field), `declared.save`
(writes `<id>.yaml`), `declared.preview` (one rule on one protocol; run here in the worker
subprocess, like every analysis). `RULES` is loaded at import; `reload_rules` below re-reads
the directory so the rules page shows a saved rule at once. Analyses run in fresh subprocesses
and see the file on their own.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.analysis import AnalysisError, slot
from api.auth import require_judge_password
from api.episodes import Gallery
from api.limits import RateLimit
from api.settings import Settings
from provette.rules import RULES, declared, sources_edit

router = APIRouter(prefix="/api/rules", tags=["declared"])

SHAPES = [
    {
        "shape": "no_carry_over",
        "words": "a tip that touched … must never go into …",
        "fields": ["carried_role", "into_role"],
    },
    {
        "shape": "full_well_not_mixed",
        "words": "a well this full must not be mixed",
        "fields": ["share", "stroke_share"],
    },
    {
        "shape": "add_after",
        "words": "… must go in after …",
        "fields": ["first", "last", "half_clause", "share"],
    },
]


class PreviewIn(BaseModel):
    rule: dict[str, Any]
    episode: str = Field(..., min_length=3, max_length=200)


class SaveIn(BaseModel):
    rule: dict[str, Any]


class SourceIn(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=1000)


def source_rows() -> list[dict[str, str]]:
    """Every source as the file holds it now, in file order."""
    return [{"key": key, **row} for key, row in sources_edit.all_sources().items()]


def declared_dir(request: Request) -> Path:
    cfg: Settings = request.app.state.settings
    return cfg.declared_dir


# The ids `RULES` took from the declared directory at import: what `reload_rules` replaces.
_declared_ids: set[str] = {p.stem for p in declared.DECLARED_DIR.glob("*.yaml")}


def reload_rules(directory: Path) -> list[str]:
    """Re-read the declared directory into `provette.rules.RULES`, keeping the Python rules, so
    the rules page shows a saved rule at once. Returns the rule ids now loaded. The engine loads
    the directory once at import and has no reload of its own; this is it (api/declared.py)."""
    global _declared_ids
    python_rules = [r for r in RULES if r.rule_id not in _declared_ids]
    loaded = declared.load_rules(directory, taken=[r.rule_id for r in python_rules])
    RULES[:] = python_rules + loaded
    _declared_ids = {r.rule_id for r in loaded}
    return [r.rule_id for r in RULES]


@router.get("/sources")
def list_sources() -> dict[str, Any]:
    return {"sources": source_rows(), "shapes": SHAPES}


@router.post("/sources")
def add_source(request: Request, body: SourceIn) -> dict[str, Any]:
    """Add one source to the file; every source, as the file holds them afterwards, comes
    back, so the form can list the new one at once."""
    require_judge_password(request, "adding a source")
    try:
        sources_edit.add_source(body.key, body.name, body.url)
    except sources_edit.SourcesEditError as error:
        raise HTTPException(422, str(error)) from error
    key = body.key.strip()
    return {
        "added": {"key": key, "name": body.name.strip(), "url": body.url.strip()},
        "sources": source_rows(),
        "shapes": SHAPES,
    }


# The declared rules as they ship with the package. On a deployment the live directory is a
# copy on the volume (PROVETTE_DECLARED_DIR); a rule there and not here was added on the site.
SHIPPED_DIR = Path(declared.__file__).parent / "declared"  # never the volume's copy


def _removable(path: Path, data: dict[str, Any], directory: Path) -> bool:
    """A rule the site may delete: added on this deployment and still proposed. A shipped rule
    and an adopted one change only through the repository."""
    added_here = (
        directory.resolve() != SHIPPED_DIR.resolve() and not (SHIPPED_DIR / path.name).is_file()
    )
    return added_here and data.get("status") != "adopted"


@router.get("/declared")
def list_declared(request: Request) -> dict[str, Any]:
    rows = []
    directory = declared_dir(request)
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("adopted_on") is not None:
            data["adopted_on"] = str(data["adopted_on"])
        rows.append({"file": path.name, **data, "removable": _removable(path, data, directory)})
    return {"rules": rows, "shapes": SHAPES}


@router.delete("/declared/{rule_id}")
def delete_declared(request: Request, rule_id: str) -> dict[str, Any]:
    """Delete a rule added on this deployment, still proposed; the rules reload, so it stops
    running from the next check."""
    require_judge_password(request, "deleting a rule")
    directory = declared_dir(request)
    path = directory / f"{rule_id}.yaml"
    if not rule_id.replace("-", "").replace("_", "").isalnum() or not path.is_file():
        raise HTTPException(404, f"no rule called {rule_id} was added here")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not _removable(path, data, directory):
        raise HTTPException(
            403,
            f"{rule_id} ships with Provette or has been adopted: it changes only through the "
            "repository",
        )
    path.unlink()
    loaded = reload_rules(directory)
    return {"deleted": rule_id, "rules_loaded": loaded}


def _final_draft_path(request: Request, episode_id: str) -> Path:
    gallery: Gallery = request.app.state.gallery
    ref = gallery.ref(episode_id)
    if ref is None:
        live = getattr(request.app.state, "live", None)
        ref = live.ref(episode_id.rsplit("/", 1)[-1]) if live is not None else None
    if ref is None:
        raise HTTPException(404, "no such episode")
    done = gallery.done(ref)
    n = (done.get("loop") or {}).get("draft")
    if n is None:
        rows = gallery.drafts(ref)
        n = rows[-1]["n"] if rows else None
    if n is None:
        raise HTTPException(404, "this episode has no draft")
    return gallery.files_dir(ref) / f"{int(n):02d}-draft.py"


preview_limit = RateLimit(n=20, per_s=60)  # per address, as /api/checks


@router.post("/preview")
def preview_rule(request: Request, body: PreviewIn) -> dict[str, Any]:
    """A rule on one episode's final draft: an Opentrons simulation in a subprocess, so it is
    bounded like a check (twenty a minute per address, and the process-wide simulation slots
    of `api.analysis.slot`, shared with the checks)."""
    preview_limit.guard(request, "previews")
    try:
        declared.validate(body.rule, body.rule.get("id") or "<preview>")
    except declared.DeclaredRuleError as error:
        raise HTTPException(422, str(error)) from error
    protocol = _final_draft_path(request, body.episode)
    cfg: Settings = request.app.state.settings
    try:
        with slot("simulations"):
            return run_preview(
                body.rule, protocol, roles_file=cfg.roles_file, sources_file=cfg.sources_file
            )
    except AnalysisError as error:
        raise HTTPException(503, str(error)) from error


def run_preview(
    rule: dict[str, Any],
    protocol: Path,
    timeout_s: float = 180,
    roles_file: Path | None = None,
    sources_file: Path | None = None,
) -> dict[str, Any]:
    """`python -m api.worker preview`: the rule on the protocol, in a subprocess."""
    with tempfile.TemporaryDirectory(prefix="provette-preview-") as tmp:
        rule_path = Path(tmp) / "rule.json"
        rule_path.write_text(json.dumps(rule), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["OT_API_CONFIG_DIR"] = str(Path(tmp) / "ot-config")
        if roles_file:
            env["PROVETTE_ROLES_FILE"] = str(roles_file)
        if sources_file:
            env["PROVETTE_SOURCES_FILE"] = str(sources_file)
        done = subprocess.run(
            [
                sys.executable,
                "-m",
                "api.worker",
                "preview",
                str(protocol),
                "--rule",
                str(rule_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            cwd=tmp,
        )
    if done.returncode != 0:
        tail = (done.stderr.strip().splitlines() or ["no output"])[-1]
        raise HTTPException(503, f"the preview failed: {tail}")
    result: dict[str, Any] = json.loads(done.stdout)
    return result


@router.post("/declared")
def save_declared(request: Request, body: SaveIn) -> dict[str, Any]:
    require_judge_password(request, "saving a rule")
    data = dict(body.rule)
    data["status"] = "proposed"  # the form proposes; adoption is our decision in the file
    data["adopted_on"] = None
    if not str(data.get("proposed_by") or "").strip():
        raise HTTPException(422, "field 'proposed_by': say who proposes the rule")
    directory = declared_dir(request)
    try:
        rule = declared.validate(data, f"{data.get('id', '<rule>')}.yaml")
        if (directory / f"{rule.id}.yaml").is_file():
            raise HTTPException(409, f"a rule called {rule.id} exists already; choose another id")
        if any(r.rule_id == rule.id for r in RULES):
            raise HTTPException(409, f"{rule.id} is the id of a rule written in Python")
        path = declared.save(data, directory)
    except declared.DeclaredRuleError as error:
        raise HTTPException(422, str(error)) from error
    loaded = reload_rules(directory)
    return {"saved": path.name, "rule": rule.to_data(), "rules_loaded": loaded}
