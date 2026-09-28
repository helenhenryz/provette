"""The pages that render a document from docs/: the rulebook we own and what it
links to. The page renders the Markdown; nothing is copied.

    GET /api/documents            the documents on offer (name, title)
    GET /api/documents/{name}     {"name", "title", "markdown"}

(`/api/docs` is FastAPI's own interactive API page.)

Only the names in DOCS are served, so a URL cannot reach an arbitrary file.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from api.settings import Settings

router = APIRouter(prefix="/api", tags=["docs"])

DOCS = {
    "rulebook": "The rulebook",
    "rule-sources": "What every rule rests on",
    "detection-catalogue": "The detection catalogue",
}


def _title(markdown: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", markdown, flags=re.M)
    return m.group(1).strip() if m else fallback


@router.get("/documents")
def list_docs(request: Request) -> dict[str, Any]:
    cfg: Settings = request.app.state.settings
    rows = []
    for name, fallback in DOCS.items():
        path = cfg.docs_dir / f"{name}.md"
        if path.is_file():
            rows.append({"name": name, "title": _title(path.read_text(encoding="utf-8"), fallback)})
    return {"docs": rows}


@router.get("/documents/{name}")
def get_doc(request: Request, name: str) -> dict[str, Any]:
    cfg: Settings = request.app.state.settings
    if name not in DOCS:
        raise HTTPException(404, "no such document")
    path = cfg.docs_dir / f"{name}.md"
    if not path.is_file():
        raise HTTPException(404, "no such document")
    markdown = path.read_text(encoding="utf-8")
    return {"name": name, "title": _title(markdown, DOCS[name]), "markdown": markdown}
