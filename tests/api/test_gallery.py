"""Contract tests for the gallery, against the frozen episodes in eval/agent/results."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.settings import REPO

REFERENCE = "super/plain/pcr-01"  # verified in 4 drafts, 9 tool calls (done.json)


def test_the_list_has_every_episode_with_a_done_json(client: TestClient) -> None:
    body = client.get("/api/episodes").json()
    sets = ("super", "nano-best3", "super-hard", "nano-hard-best3")
    on_disk = sum(1 for s in sets for _ in (REPO / "eval/agent/results" / s).glob("*/*/done.json"))
    assert len(body["episodes"]) == on_disk >= 20
    assert body["sets"] == list(sets)
    hard = next(e for e in body["episodes"] if e["set"] == "super-hard")
    assert hard["request_id"].startswith("hard-") and hard["request"] and hard["technique"]
    best = next(e for e in body["episodes"] if e["set"] == "nano-best3")
    assert best["candidates"]["n"] == 3 and best["run_label"] == "best of 3"
    card = next(e for e in body["episodes"] if e["id"] == REFERENCE)
    assert card["model_label"] == "Nemotron 3 Super 120B"
    assert card["request"].startswith("Set up PCR reactions for 8 DNA samples")
    assert card["technique"] == "PCR setup"
    assert card["condition_label"] == "the request as written"
    assert card["run_label"] == "one try"
    assert card["verified"] is True
    assert card["outcome"]["sentence"].startswith("Verified")


def test_cost_is_computed_from_the_prices_file_not_typed(client: TestClient) -> None:
    card = next(e for e in client.get("/api/episodes").json()["episodes"] if e["id"] == REFERENCE)
    prices = json.loads((REPO / "eval/prices.json").read_text())["models"][card["model"]]
    expected = (
        card["tokens_in"] * prices["input_per_million_usd"]
        + card["tokens_out"] * prices["output_per_million_usd"]
    ) / 1e6
    assert card["cost_usd"] == pytest.approx(expected, abs=1e-4)


def test_verified_matches_the_evaluations_definition(client: TestClient) -> None:
    for card in client.get("/api/episodes").json()["episodes"]:
        done = json.loads((REPO / "eval/agent/results" / card["id"] / "done.json").read_text())
        loop = done["loop"]
        expected = (
            loop["simulator"] == "passed" and loop["verify_exit"] == 0 and loop["check_exit"] == 0
        )
        assert card["verified"] == expected, card["id"]


def test_the_story_has_steps_drafts_and_the_plate_map(client: TestClient) -> None:
    body = client.get(f"/api/episodes/{REFERENCE}").json()
    assert body["platemap"]["id"] == "pcr-01"
    assert body["final_draft"] == 3
    assert [d["n"] for d in body["draft_rows"]] == [0, 1, 2, 3]
    assert body["draft_rows"][3]["summary"]["status"] == "ok"
    assert body["draft_rows"][0]["summary"]["status"] == "rejected"
    titles = [s["title"] for s in body["steps"]]
    assert titles[0] == "Read the plate map"
    assert any(t.startswith("Looked up the labware") for t in titles)
    assert any(t.startswith("Draft 0: the simulator rejected the file at line") for t in titles)
    assert any(t.startswith("Draft 3: verified 8 of 8 wells") for t in titles)
    assert titles[-1] == "Submitted draft 3"
    assert all(s["status"] in ("ok", "rejected", "problem", "info") for s in body["steps"])


def test_a_draft_returns_its_text_and_checks(client: TestClient) -> None:
    body = client.get(f"/api/episodes/{REFERENCE}/drafts/0").json()
    assert body["text"].startswith("from opentrons import protocol_api")
    assert body["checks"]["simulator"] == "rejected"
    assert client.get(f"/api/episodes/{REFERENCE}/drafts/9").status_code == 404  # 4 drafts
    assert client.get("/api/episodes/no/such/thing").status_code == 404


def test_the_protocol_download_is_the_final_draft(client: TestClient) -> None:
    text = client.get(f"/api/episodes/{REFERENCE}/protocol.py").text
    on_disk = (REPO / "eval/agent/results" / REFERENCE / "03-draft.py").read_text()
    assert text == on_disk


@pytest.mark.sim
def test_the_analysis_is_the_pipelines_own_json_and_is_cached(client: TestClient) -> None:
    body = client.get(f"/api/episodes/{REFERENCE}/analysis").json()
    assert body["simulator"]["passed"] is True
    assert body["check"]["schema_version"] == 1
    assert body["verify"]["intent"]["status"] == "verified"
    assert body["verify"]["intent"]["wells_ok"] == 8
    assert body["replay"]["events"] and body["replay"]["deck"]
    # The second read comes from the cache: no simulator, same answer.
    again = client.get(f"/api/episodes/{REFERENCE}/analysis").json()
    assert again == body
    page = client.get(f"/api/episodes/{REFERENCE}/replay.html").text
    assert "Provette replay" in page and "provette-data" in page


@pytest.mark.sim
def test_rules_lists_every_rule_with_its_sources(client: TestClient) -> None:
    body = client.get("/api/rules").json()
    ids = {r["rule_id"] for r in body["rules"]}
    assert {"CONTAM-STOCK", "CONTAM-WELL", "MIX-BEFORE-DRAW", "PIPETTE-RANGE"} <= ids
    assert all(r["sources"] and r["description"] for r in body["rules"])


def test_the_default_gallery_is_the_four_agent_runs_and_each_has_results() -> None:
    """The deployment's gallery (no PROVETTE_GALLERY_SETS set) shows the four runs of
    eval/agent/README.md, and every one has result files under eval/."""
    from api.settings import settings_from_env

    settings = settings_from_env()
    assert settings.gallery_sets == ("super", "nano-best3", "super-hard", "nano-hard-best3")
    for name in settings.gallery_sets:
        assert any((settings.episodes_dir / name).glob("*/*/done.json")), name
