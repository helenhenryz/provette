"""The failed-run record and the coverage panel's data."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings
from tests.api.conftest import make_settings

EPISODE = "super/plain/pcr-01"
PASSWORD = "judge-secret"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    base = make_settings(tmp_path)
    with TestClient(create_app(Settings(**{**base.__dict__, "judge_password": PASSWORD}))) as c:
        yield c


def test_an_outcome_needs_the_password_and_a_note_when_no(client: TestClient) -> None:
    assert (
        client.post(
            "/api/outcomes", json={"episode": EPISODE, "ok": False, "note": "x"}
        ).status_code
        == 401
    )
    h = {"x-judge-password": PASSWORD}
    r = client.post(
        "/api/outcomes", json={"episode": EPISODE, "ok": False, "note": "  "}, headers=h
    )
    assert r.status_code == 422 and "which wells" in r.json()["detail"]
    r = client.post(
        "/api/outcomes", json={"episode": "no/such/one", "ok": True, "note": ""}, headers=h
    )
    assert r.status_code == 404


def test_records_are_kept_and_the_failures_listed_with_their_request(
    client: TestClient, tmp_path: Path
) -> None:
    h = {"x-judge-password": PASSWORD}
    r = client.post(
        "/api/outcomes",
        json={
            "episode": EPISODE,
            "ok": False,
            "note": "Wells A1 to A4 were   pink.\nThe master mix was old.",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    row = r.json()
    assert row["set"] == "super" and row["ok"] is False
    assert row["note"] == "Wells A1 to A4 were pink. The master mix was old."
    lines = (tmp_path / "data" / "outcomes.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["episode"] == EPISODE
    mine = client.get(f"/api/outcomes?episode={EPISODE}").json()
    assert mine["latest"]["note"].startswith("Wells A1")
    everything = client.get("/api/outcomes").json()
    assert len(everything["failures"]) == 1
    failure = everything["failures"][0]
    assert (
        failure["request"].startswith("Set up PCR reactions")
        and failure["technique"] == "PCR setup"
    )
    # a later "yes" replaces the record; the failure list follows the latest
    client.post("/api/outcomes", json={"episode": EPISODE, "ok": True, "note": ""}, headers=h)
    assert client.get("/api/outcomes").json()["failures"] == []
    assert client.get(f"/api/outcomes?episode={EPISODE}").json()["latest"]["ok"] is True


def test_outcomes_are_off_without_a_password(tmp_path: Path) -> None:
    with TestClient(create_app(make_settings(tmp_path))) as c:
        r = c.post("/api/outcomes", json={"episode": EPISODE, "ok": True, "note": ""})
        assert r.status_code == 503 and "judge password" in r.json()["detail"]
        assert c.get("/api/outcomes").json() == {"records": [], "failures": []}


def test_coverage_matches_the_technique_or_falls_back(client: TestClient) -> None:
    pcr = client.get("/api/coverage?technique=PCR%20setup").json()
    assert pcr["matched"] is True and pcr["key"] == "PCR setup"
    assert pcr["checked"][0].startswith("Every reaction well") and len(pcr["physics"]) == 1
    lower = client.get("/api/coverage?technique=pcr%20setup").json()
    assert lower["matched"] is True
    other = client.get("/api/coverage?technique=Bead%20cleanup").json()
    assert (
        other["matched"] is False
        and other["key"] == "default"
        and other["technique"] == "Bead cleanup"
    )
    assert other["not_checked"][0].startswith("Anything specific")
    none = client.get("/api/coverage").json()
    assert none["technique"] is None and none["key"] == "default" and none["available"] is True


def test_coverage_without_the_file_says_so(tmp_path: Path) -> None:
    base = make_settings(tmp_path)
    with TestClient(
        create_app(Settings(**{**base.__dict__, "coverage_file": tmp_path / "none.yaml"}))
    ) as c:
        body = c.get("/api/coverage?technique=PCR%20setup").json()
        assert body["available"] is False and body["checked"] == [] and body["source"] is None


def test_every_technique_is_listed_with_its_lists(client: TestClient) -> None:
    body = client.get("/api/coverage/techniques").json()
    names = [row["technique"] for row in body["techniques"]]
    assert "PCR setup" in names and names[-1] == "default"
    pcr = next(row for row in body["techniques"] if row["technique"] == "PCR setup")
    assert pcr["checked"] and pcr["not_checked"] and "physics" in pcr
    assert body["source"] == "coverage.yaml"
