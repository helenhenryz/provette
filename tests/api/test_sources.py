"""`GET /api/rules/sources` reads the sources file on each call; `POST /api/rules/sources` adds
one behind the judge password and writes it to the file `sources.SOURCES_FILE` points at (a copy
under tmp_path here, as `PROVETTE_SOURCES_FILE` would point a deployment elsewhere)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings
from provette.rules import declared, sources
from tests.api.conftest import make_settings

PASSWORD = "open-sesame"
NEW = {"key": "MY_LAB_MANUAL", "name": "My lab's manual: keep it on ice", "url": "https://x.org/m"}


@pytest.fixture
def scratch_sources(tmp_path: Path) -> Iterator[Path]:
    copy = tmp_path / "sources.yaml"
    copy.write_text(sources.SOURCES_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    original = sources.SOURCES_FILE
    try:
        yield copy
    finally:
        sources.SOURCES_FILE = original
        sources.reload(original)


def _settings(tmp_path: Path, password: str, sources_file: Path) -> Settings:
    base = make_settings(tmp_path)
    return Settings(**{**base.__dict__, "judge_password": password, "sources_file": sources_file})


def test_the_sources_route_reads_the_file(scratch_sources: Path, tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path, "", scratch_sources))) as c:
        rows = c.get("/api/rules/sources").json()["sources"]
        assert [r["key"] for r in rows] == list(sources.SOURCES)
        assert all(r["name"] and r["url"].startswith("http") for r in rows)
        # an entry written by hand shows on the next read, with no restart
        scratch_sources.write_text(
            scratch_sources.read_text(encoding="utf-8")
            + "BY_HAND:\n  name: added by hand\n  url: https://x.org/h\n",
            encoding="utf-8",
        )
        assert c.get("/api/rules/sources").json()["sources"][-1]["key"] == "BY_HAND"


def test_adding_a_source_needs_the_password(scratch_sources: Path, tmp_path: Path) -> None:
    before = scratch_sources.read_text(encoding="utf-8")
    with TestClient(create_app(_settings(tmp_path, "", scratch_sources))) as c:
        assert c.post("/api/rules/sources", json=NEW).status_code == 503
    with TestClient(create_app(_settings(tmp_path, PASSWORD, scratch_sources))) as c:
        assert c.post("/api/rules/sources", json=NEW).status_code == 401
        wrong = {"X-Judge-Password": "no"}
        assert c.post("/api/rules/sources", json=NEW, headers=wrong).status_code == 401
    assert scratch_sources.read_text(encoding="utf-8") == before
    assert NEW["key"] not in sources.SOURCES


def test_adding_a_source_writes_the_copy_and_a_rule_may_cite_it(
    scratch_sources: Path, tmp_path: Path
) -> None:
    headers = {"X-Judge-Password": PASSWORD}
    with TestClient(create_app(_settings(tmp_path, PASSWORD, scratch_sources))) as c:
        assert scratch_sources == sources.SOURCES_FILE  # the app writes the copy
        answer = c.post("/api/rules/sources", json=NEW, headers=headers)
        assert answer.status_code == 200, answer.text
        assert answer.json()["added"] == NEW
        assert answer.json()["sources"][-1] == NEW
        assert c.get("/api/rules/sources").json()["sources"][-1] == NEW
        # the registry the rule form validates against knows it at once
        assert NEW["key"] in declared.SOURCES
        assert declared.validate({**RULE, "sources": [NEW["key"]]}, "x.yaml").source_keys == (
            NEW["key"],
        )
        # refused: a duplicate, a bad key, a bad url, an empty name
        again = c.post("/api/rules/sources", json=NEW, headers=headers)
        assert again.status_code == 422 and "already" in again.json()["detail"]
        bad_key = c.post("/api/rules/sources", json={**NEW, "key": "my lab"}, headers=headers)
        assert bad_key.status_code == 422 and "not a source key" in bad_key.json()["detail"]
        bad_url = c.post(
            "/api/rules/sources", json={**NEW, "key": "X2", "url": "x.org"}, headers=headers
        )
        assert bad_url.status_code == 422 and "not a link" in bad_url.json()["detail"]
        assert (
            c.post(
                "/api/rules/sources", json={**NEW, "key": "X3", "name": " "}, headers=headers
            ).status_code
            == 422
        )
    text = scratch_sources.read_text(encoding="utf-8")
    assert text.endswith(f'{NEW["key"]}:\n  name: "{NEW["name"]}"\n  url: "{NEW["url"]}"\n')
    assert "X2" not in text and "X3" not in text


RULE = {
    "id": "TEST-RULE",
    "shape": "add_after",
    "title": "a test",
    "severity": "note",
    "first": "add_first",
    "last": "add_last",
    "half_clause": True,
    "why": "Because.",
    "fix": "Do it the other way round.",
    "sources": ["THERMO_RESTRICTION_ENZYMES"],
    "proposed_by": "a test",
    "status": "proposed",
    "adopted_on": None,
}
