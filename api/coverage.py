"""What the checks cover for a technique, and what they do not: the coverage panel's data.

    GET /api/coverage?technique=PCR%20setup
    GET /api/coverage/techniques         every technique the file names, each with its lists

Reads `provette/rules/coverage.yaml` (`PROVETTE_COVERAGE_FILE`
overrides), keyed by technique, each with `checked`, `not_checked` and `physics` lists of
plain sentences and a `default` entry for a technique the file does not name. Silence is not
safety: the page says what was not looked at, and that the physics never is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Request

from api.settings import Settings

router = APIRouter(prefix="/api", tags=["coverage"])

KEYS = ("checked", "not_checked", "physics")


def load(path: Path) -> dict[str, dict[str, list[str]]]:
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, list[str]]] = {}
    for technique, entry in raw.items() if isinstance(raw, dict) else []:
        if not isinstance(entry, dict):
            continue
        out[str(technique)] = {
            k: [s for s in (_sentence(x) for x in (entry.get(k) or [])) if s] for k in KEYS
        }
    return out


def _sentence(item: Any) -> str:
    """One plain sentence. A sentence with a colon that YAML read as a one-key mapping
    ("Anything specific: nothing knows it") is put back together."""
    if isinstance(item, dict) and len(item) == 1:
        ((key, value),) = item.items()
        return f"{key}: {value}".strip()
    return str(item).strip()


def _match(table: dict[str, dict[str, list[str]]], technique: str | None) -> tuple[str, bool]:
    """The entry's key for a technique: exact, then case-insensitive, then the first word
    ("PCR setup" for "qPCR setup" is not a match; "pcr setup" is), else `default`."""
    if technique:
        if technique in table:
            return technique, True
        lowered = {k.lower(): k for k in table}
        if technique.lower() in lowered:
            return lowered[technique.lower()], True
    return "default", False


def coverage_for(path: Path, technique: str | None) -> dict[str, Any]:
    table = load(path)
    key, matched = _match(table, technique)
    entry = table.get(key) or {k: [] for k in KEYS}
    return {
        "technique": technique,
        "matched": matched,
        "key": key if key in table else None,
        "available": bool(table),
        "source": str(path.name) if path.is_file() else None,
        **entry,
    }


@router.get("/coverage")
def coverage(request: Request, technique: str | None = None) -> dict[str, Any]:
    cfg: Settings = request.app.state.settings
    return coverage_for(cfg.coverage_file, technique)


@router.get("/coverage/techniques")
def techniques(request: Request) -> dict[str, Any]:
    """Every technique the file names, in the file's order, with its three lists; `default`
    last, as the entry a technique the file does not name gets."""
    cfg: Settings = request.app.state.settings
    table = load(cfg.coverage_file)
    rows = [{"technique": k, **v} for k, v in table.items() if k != "default"]
    if "default" in table:
        rows.append({"technique": "default", **table["default"]})
    return {
        "techniques": rows,
        "source": cfg.coverage_file.name if cfg.coverage_file.is_file() else None,
    }
