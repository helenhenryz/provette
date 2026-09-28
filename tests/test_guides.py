"""CLAUDE.md and AGENTS.md are one operating guide under two names, for the agents that read
each: from "## The mission" down they must say the same thing, so they cannot drift apart."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def body(name: str) -> str:
    text = (ROOT / name).read_text(encoding="utf-8")
    return text[text.index("## The mission") :]


def test_the_two_guides_say_the_same_thing() -> None:
    assert body("CLAUDE.md") == body("AGENTS.md")
