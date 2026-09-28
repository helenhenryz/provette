"""Teaching a word, and declaring a rule: the two ways the product learns without code."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import REPO, Settings
from provette.rules import roles as roles_module
from tests.api.conftest import make_settings

PASSWORD = "judge-secret"
LYSOZYME = """from opentrons import protocol_api

metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    lys = protocol.define_liquid("lysozyme", description="lysozyme stock", display_color="#00ff00")
    rack["A1"].load_liquid(lys, 200)
    for well in ["A1", "A2", "A3"]:
        p20.transfer(5, rack["A1"], plate[well], new_tip="always")
"""


@pytest.fixture(autouse=True)
def _rules_restored() -> Iterator[None]:
    """Saving a rule reloads the shared `provette.rules.RULES` in place (api/declared.py,
    `reload_rules`); put it back after each test, so a test rule never runs in a later test
    on the same worker."""
    import api.declared as declared_api
    from provette.rules import RULES

    rules, ids = list(RULES), set(declared_api._declared_ids)
    yield
    RULES[:] = rules
    declared_api._declared_ids = ids


ENZYME_RULE = {
    "id": "TEST-ENZYME-LAST",
    "shape": "add_after",
    "title": "An enzyme was added before the water",
    "severity": "warning",
    "first": "add_first",
    "last": "add_last",
    "half_clause": True,
    "why": "An enzyme meets too much salt in a dry well.",
    "fix": "Water first, then the sample, then {liquids} last into {wells}.",
    "sources": ["THERMO_RESTRICTION_ENZYMES"],
    "proposed_by": "a test",
    "status": "proposed",
    "adopted_on": None,
}


def roles_copy_path(tmp_path: Path) -> Path:
    return tmp_path / "roles.yaml"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """The app with the word lists and the declared directory copied to tmp, so a test never
    writes into provette/rules."""
    roles_copy = tmp_path / "roles.yaml"
    shutil.copy(roles_module.ROLES_FILE, roles_copy)
    declared_copy = tmp_path / "declared"
    shutil.copytree(REPO / "provette/rules/declared", declared_copy)
    base = make_settings(tmp_path)
    original = roles_module.ROLES_FILE
    settings = Settings(
        **{
            **base.__dict__,
            "judge_password": PASSWORD,
            "roles_file": roles_copy,
            "declared_dir": declared_copy,
        }
    )
    try:
        with TestClient(create_app(settings)) as c:
            yield c
    finally:
        roles_module.ROLES_FILE = original
        roles_module.reload(original)


def test_the_seven_lists_are_served(client: TestClient) -> None:
    body = client.get("/api/roles").json()
    assert set(body["list_names"]) == {
        "sample",
        "reagent",
        "carrier",
        "add_last",
        "add_first",
        "mix",
        "rt",
    }
    assert "water" in body["lists"]["carrier"]


def test_teaching_a_word_needs_the_password_and_lands_in_the_copy(
    client: TestClient, tmp_path: Path
) -> None:
    assert client.post("/api/roles/reagent", json={"word": "lysozyme"}).status_code == 401
    h = {"x-judge-password": PASSWORD}
    r = client.post("/api/roles/nonsense", json={"word": "lysozyme"}, headers=h)
    assert r.status_code == 422 and "no list called" in r.json()["detail"]
    r = client.post("/api/roles/reagent", json={"word": "lysozyme"}, headers=h)
    assert r.status_code == 200 and "lysozyme" in r.json()["lists"]["reagent"]
    assert "lysozyme" in (tmp_path / "roles.yaml").read_text()
    assert roles_copy_path(tmp_path) == roles_module.ROLES_FILE  # the app writes the copy
    r = client.post("/api/roles/reagent", json={"word": "lysozyme"}, headers=h)
    assert r.status_code == 422  # already there


@pytest.mark.sim
def test_an_unplaced_liquid_is_reported_then_placed_and_the_check_reruns(
    client: TestClient,
) -> None:
    first = client.post("/api/checks", json={"protocol": LYSOZYME, "name": "lysozyme.py"}).json()
    names = [u["name"] for u in first["analysis"]["check"]["unplaced_liquids"]]
    assert names == ["lysozyme"]
    assert (
        "I do not know what 'lysozyme' is"
        in first["analysis"]["check"]["unplaced_liquids"][0]["sentence"]
    )
    r = client.post(
        "/api/roles/reagent", json={"word": "lysozyme"}, headers={"x-judge-password": PASSWORD}
    )
    assert r.status_code == 200
    # The cache key carries the word lists' digest, so the same protocol is analysed afresh.
    second = client.post("/api/checks", json={"protocol": LYSOZYME, "name": "lysozyme.py"}).json()
    assert second["analysis"]["check"]["unplaced_liquids"] == []


def test_sources_and_declared_rules_are_listed(client: TestClient) -> None:
    body = client.get("/api/rules/sources").json()
    keys = {s["key"] for s in body["sources"]}
    assert "THERMO_RESTRICTION_ENZYMES" in keys and all(
        s["name"] and s["url"] for s in body["sources"]
    )
    assert [s["shape"] for s in body["shapes"]] == [
        "no_carry_over",
        "full_well_not_mixed",
        "add_after",
    ]
    rules = client.get("/api/rules/declared").json()["rules"]
    enzyme = next(r for r in rules if r["id"] == "ENZYME-BEFORE-DILUENT")
    assert enzyme["status"] == "adopted" and enzyme["shape"] == "add_after"
    listed = {r["rule_id"]: r for r in client.get("/api/rules").json()["rules"]}
    assert listed["ENZYME-BEFORE-DILUENT"]["status"] == "adopted"
    assert listed["ENZYME-BEFORE-DILUENT"]["proposed_by"]


@pytest.mark.sim
def test_preview_runs_a_rule_on_an_episodes_final_draft(client: TestClient) -> None:
    r = client.post(
        "/api/rules/preview",
        json={
            "rule": {**ENZYME_RULE, "sources": ["NOPE"]},
            "episode": "super/plain/pcr-01",
        },
    )
    assert r.status_code == 422 and "sources" in r.json()["detail"]
    r = client.post(
        "/api/rules/preview", json={"rule": ENZYME_RULE, "episode": "super/plain/clone-01"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["simulator"]["passed"] in (True, False)
    assert isinstance(body["findings"], list)
    assert (
        client.post(
            "/api/rules/preview", json={"rule": ENZYME_RULE, "episode": "no/such/one"}
        ).status_code
        == 404
    )


def test_saving_a_rule_writes_the_file_as_proposed_and_reloads(
    client: TestClient, tmp_path: Path
) -> None:
    h = {"x-judge-password": PASSWORD}
    assert client.post("/api/rules/declared", json={"rule": ENZYME_RULE}).status_code == 401
    bad = {**ENZYME_RULE, "id": "TEST-BAD", "first": "add_last"}
    r = client.post("/api/rules/declared", json={"rule": bad}, headers=h)
    assert r.status_code == 422 and "last" in r.json()["detail"]
    r = client.post(
        "/api/rules/declared", json={"rule": {**ENZYME_RULE, "status": "adopted"}}, headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["saved"] == "TEST-ENZYME-LAST.yaml" and body["rule"]["status"] == "proposed"
    assert (tmp_path / "declared" / "TEST-ENZYME-LAST.yaml").is_file()
    assert "TEST-ENZYME-LAST" in body["rules_loaded"] and "CONTAM-STOCK" in body["rules_loaded"]
    ids = [r["rule_id"] for r in client.get("/api/rules").json()["rules"]]
    assert "TEST-ENZYME-LAST" in ids and "ENZYME-BEFORE-DILUENT" in ids
    assert (
        client.post("/api/rules/declared", json={"rule": ENZYME_RULE}, headers=h).status_code == 409
    )
    assert (
        client.post(
            "/api/rules/declared", json={"rule": {**ENZYME_RULE, "id": "CONTAM-STOCK"}}, headers=h
        ).status_code
        == 409
    )
