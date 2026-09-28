"""`GET /api/roles` shows the word lists; `POST /api/roles/{list}` adds a word behind the judge
password, and writes it to the file `roles.ROLES_FILE` points at (a copy under tmp_path here)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings
from provette.rules import roles
from tests.api.conftest import make_settings

PASSWORD = "open-sesame"


@pytest.fixture
def scratch_roles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    copy = tmp_path / "roles.yaml"
    copy.write_text(roles.ROLES_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(roles, "ROLES_FILE", copy)
    roles.reload()
    yield copy
    monkeypatch.undo()
    roles.reload()


def _settings(tmp_path: Path, password: str) -> Settings:
    base = make_settings(tmp_path)
    return Settings(**{**base.__dict__, "judge_password": password})


def test_the_roles_route_lists_the_seven_lists(client: TestClient) -> None:
    data = client.get("/api/roles").json()
    assert data["list_names"] == list(roles.LIST_NAMES)
    assert data["lists"] == roles.lists()
    assert "water" in data["lists"]["carrier"]
    assert "a sample, a reagent, a carrier" in data["places"]


def test_adding_a_word_needs_a_password_on_this_deployment(
    tmp_path: Path, scratch_roles: Path
) -> None:
    body = {"word": "lysozyme"}
    with TestClient(create_app(_settings(tmp_path, ""))) as c:
        assert c.post("/api/roles/reagent", json=body).status_code == 503
    with TestClient(create_app(_settings(tmp_path, PASSWORD))) as c:
        assert c.post("/api/roles/reagent", json=body).status_code == 401
        wrong = {"X-Judge-Password": "no"}
        assert c.post("/api/roles/reagent", json=body, headers=wrong).status_code == 401
    # the file's top comment shows "- lysozyme" as the example; no list line was added
    assert "  - lysozyme" not in scratch_roles.read_text(encoding="utf-8").splitlines()
    assert roles.role_of("lysozyme") is None


def test_adding_a_word_writes_the_file_and_the_lists_follow(
    tmp_path: Path, scratch_roles: Path
) -> None:
    headers = {"X-Judge-Password": PASSWORD}
    with TestClient(create_app(_settings(tmp_path, PASSWORD))) as c:
        answer = c.post("/api/roles/reagent", json={"word": "lysozyme"}, headers=headers)
        assert answer.status_code == 200
        assert answer.json()["added"] == {"list": "reagent", "word": "lysozyme"}
        assert answer.json()["lists"]["reagent"][-1] == "lysozyme"
        assert c.get("/api/roles").json()["lists"]["reagent"][-1] == "lysozyme"
        # refused: a duplicate, an unknown list, an empty word
        again = c.post("/api/roles/reagent", json={"word": "Lysozyme"}, headers=headers)
        assert again.status_code == 422 and "already" in again.json()["detail"]
        assert c.post("/api/roles/enzymes", json={"word": "x"}, headers=headers).status_code == 422
        assert c.post("/api/roles/reagent", json={"word": ""}, headers=headers).status_code == 422
    assert "  - lysozyme\n" in scratch_roles.read_text(encoding="utf-8")
    assert roles.role_of("lysozyme") == "reagent"
