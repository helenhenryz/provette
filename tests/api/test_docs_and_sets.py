"""The rendered documents, and an episode from the harder request set (eval/requests-hard)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import REPO, Settings
from tests.api.conftest import make_settings


def test_the_rulebook_and_what_it_links_to_are_served_and_nothing_else(
    client: TestClient,
) -> None:
    names = {d["name"] for d in client.get("/api/documents").json()["docs"]}
    assert names == {"rulebook", "rule-sources", "detection-catalogue"}
    book = client.get("/api/documents/rulebook").json()
    assert book["title"] == "The rulebook" and "CONTAM-STOCK" in book["markdown"]
    assert client.get("/api/documents/notes").status_code == 404
    assert client.get("/api/documents/hackathon").status_code == 404
    assert client.get("/api/documents/how-it-works").status_code == 404


def test_the_rules_route_lists_every_rule_in_RULES(client: TestClient) -> None:
    from provette.rules import RULES

    ids = [r["rule_id"] for r in client.get("/api/rules").json()["rules"]]
    assert ids == [r.rule_id for r in RULES] and len(ids) >= 11


def hard_settings(tmp_path: Path) -> Settings:
    """A result set for a request of eval/requests-hard, built from a real episode's files."""
    source = REPO / "eval/agent/results/super/plain/pcr-01"
    root = tmp_path / "results" / "hard" / "plain" / "hard-pcr-01"
    shutil.copytree(source, root)
    done = json.loads((source / "done.json").read_text())
    done["id"] = "hard-pcr-01"
    (root / "done.json").write_text(json.dumps(done))
    base = make_settings(tmp_path, sets=("hard",))
    return Settings(**{**base.__dict__, "episodes_dir": tmp_path / "results"})


def test_an_episode_of_the_harder_set_finds_its_request_and_map(tmp_path: Path) -> None:
    with TestClient(create_app(hard_settings(tmp_path))) as client:
        card = client.get("/api/episodes").json()["episodes"][0]
        hard = {
            json.loads(line)["id"]: json.loads(line)
            for line in (REPO / "eval/requests-hard/requests.jsonl").read_text().splitlines()
            if line.strip()
        }
        assert card["request"] == hard["hard-pcr-01"]["request"]
        assert card["technique"] == hard["hard-pcr-01"]["technique"]
        body = client.get("/api/episodes/hard/plain/hard-pcr-01").json()
        assert body["platemap"]["id"] == "hard-pcr-01"
        assert body["platemap"].get("technique")
        # the check page offers the harder maps too
        maps = {m["id"] for m in client.get("/api/platemaps").json()["platemaps"]}
        assert {"pcr-01", "hard-pcr-01", "hard-dil-01"} <= maps
        assert client.get("/api/platemaps/hard-dil-01").json()["id"] == "hard-dil-01"
