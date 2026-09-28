"""The rules page's data: every rule `provette check` runs, as `check --json` lists them; and
the word lists that say what a declared liquid is (`provette/rules/roles.yaml`).

    GET  /api/rules                       every rule in `provette.rules.RULES`, with its sources
    GET  /api/roles                       {"lists": {"sample": [...], ...}, "list_names": [...]}
    POST /api/roles/{list}  {"word": s}   adds a word to that list (judge password, as the
                                          live flow: header X-Judge-Password); 503 when no
                                          password is set on this deployment

A rule that lands in `provette/rules/RULES` appears here the same day, with its description; the
sources are the rule's own (`Source`: name and url, copied from `docs/rule-sources.md`).
`status` is "adopted" or "proposed" (a proposed rule's findings are notes and never block) and
`proposed_by` says who wrote it; both come from the rule's file for a declared rule.
sources are the rule's own (`Source`: name and url, copied from `docs/rule-sources.md`). A word
added here is written to `roles.yaml` in the running checkout (`provette.rules.roles_edit`), so
the next check, in its own subprocess, reads it.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import require_judge_password
from provette.rules import RULES, SCHEMA_VERSION, roles_edit
from provette.rules.roles import LIST_NAMES, PLACES

router = APIRouter(prefix="/api", tags=["rules"])


@router.get("/rules")
def rules() -> dict[str, Any]:
    rows = []
    for rule in RULES:
        row: dict[str, Any] = {
            "rule_id": rule.rule_id,
            "family": rule.family,
            "tier": rule.tier,
            "description": rule.description,
            "title": rule.title,
            "sources": [{"name": s.name, "url": s.url} for s in rule.sources],
            "status": rule.status,
            "proposed_by": rule.proposed_by,
        }
        rows.append(row)
    return {"schema_version": SCHEMA_VERSION, "rules": rows}


class WordRequest(BaseModel):
    word: str = Field(min_length=1, max_length=200)


def _roles_answer() -> dict[str, Any]:
    return {"list_names": list(LIST_NAMES), "places": PLACES, "lists": roles_edit.lists()}


@router.get("/roles")
def roles() -> dict[str, Any]:
    """The word lists we own, as the file holds them."""
    return _roles_answer()


@router.post("/roles/{list_name}")
def add_role_word(request: Request, list_name: str, body: WordRequest) -> dict[str, Any]:
    """Add one word to one list; the lists as they are afterwards come back."""
    require_judge_password(request)
    try:
        roles_edit.add_word(list_name, body.word)
    except roles_edit.RolesEditError as error:
        raise HTTPException(422, str(error)) from error
    return {"added": {"list": list_name, "word": body.word.strip()}, **_roles_answer()}
