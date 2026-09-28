"""Flow 3, end to end: the reference fixture with planted bugs, checked through the API."""

from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from api.limits import RateLimit
from api.settings import REPO

FIXTURE = REPO / "tests/fixtures/protocols/pcr_buggy.py"
PLATEMAP = REPO / "eval/platemaps/pcr-01.json"


@pytest.mark.sim
def test_pcr_buggy_shows_its_findings_and_replay_in_under_fifteen_seconds(
    client: TestClient,
) -> None:
    started = time.time()
    response = client.post(
        "/api/checks",
        json={
            "protocol": FIXTURE.read_text(),
            "platemap": PLATEMAP.read_text(),
            "name": "pcr_buggy.py",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert time.time() - started < 15
    analysis = body["analysis"]
    assert analysis["simulator"]["passed"] is True
    assert analysis["check"]["counts"]["by_severity"]["error"] >= 1
    assert analysis["check"]["findings"][0]["rule_id"] == "CONTAM-STOCK"
    assert analysis["verify"]["intent"]["status"] == "mismatch"
    assert analysis["replay"]["events"]
    assert body["platemap"]["id"] == "pcr-01"
    # The check is kept at its URL.
    again = client.get(f"/api/checks/{body['id']}").json()
    assert again["analysis"] == analysis
    assert again["protocol"] == FIXTURE.read_text()
    page = client.get(f"/api/checks/{body['id']}/replay.html")
    assert page.status_code == 200 and "provette-data" in page.text
    assert client.get(f"/api/checks/{body['id']}/protocol.py").text == FIXTURE.read_text()


RUNS_DRY = """
from opentrons import protocol_api

metadata = {"apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    buffer = protocol.define_liquid("buffer", description="PBS", display_color="#0000FF")
    tubes["A1"].load_liquid(buffer, 150)  # 150 µl declared, 300 µl drawn: it runs dry
    p300.pick_up_tip()
    for well in ("A1", "A2", "A3"):
        p300.aspirate(100, tubes["A1"])
        p300.dispense(100, plate[well])
    p300.drop_tip()
"""


@pytest.mark.sim
def test_the_prep_sheet_comes_without_a_plate_map_and_says_what_runs_dry(
    client: TestClient,
) -> None:
    response = client.post("/api/checks", json={"protocol": RUNS_DRY, "name": "dry.py"})
    assert response.status_code == 200, response.text
    analysis = response.json()["analysis"]
    assert analysis["verify"] is None  # no plate map: nothing to verify against
    prep = analysis["prep"]
    lines = {(line["slot"], line["well"]): line for line in prep["lines"]}
    tube = lines[("2", "A1")]
    assert tube["liquid"] == "buffer"
    assert tube["declared_ul"] == 150
    assert tube["needed_ul"] == 300
    assert tube["flag"] == "would_run_dry"
    assert prep["tips"] == [{"slot": "1", "rack": "Opentrons OT-2 96 Tip Rack 300 µL", "tips": 1}]
    # with a plate map the same sheet is under verify.prep as before
    with_map = client.post(
        "/api/checks", json={"protocol": FIXTURE.read_text(), "platemap": PLATEMAP.read_text()}
    ).json()["analysis"]
    assert with_map["prep"] == with_map["verify"]["prep"]


@pytest.mark.sim
def test_a_rejected_protocol_is_reported_not_crashed(client: TestClient) -> None:
    response = client.post("/api/checks", json={"protocol": "def run(protocol):\n    1/0\n"})
    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["simulator"]["passed"] is False
    assert analysis["simulator"]["error"]
    assert analysis["replay"] is None
    assert analysis["prep"] is None


@pytest.mark.sim
def test_the_checks_are_listed_newest_first_as_small_rows(client: TestClient) -> None:
    assert client.get("/api/checks").json()["checks"] == []
    buggy = client.post(
        "/api/checks",
        json={
            "protocol": FIXTURE.read_text(),
            "platemap": PLATEMAP.read_text(),
            "name": "pcr_buggy.py",
        },
    ).json()
    time.sleep(0.01)
    broken = client.post("/api/checks", json={"protocol": "def run(protocol):\n    1/0\n"}).json()
    rows = client.get("/api/checks").json()["checks"]
    assert [r["id"] for r in rows] == [broken["id"], buggy["id"]]
    assert rows[1] == {
        "id": buggy["id"],
        "name": "pcr_buggy.py",
        "created": buggy["created"],
        "simulator": "passed",
        "findings": len(buggy["analysis"]["check"]["findings"]),
        "has_map": True,
    }
    assert rows[0]["simulator"] == "rejected" and rows[0]["findings"] == 0
    assert rows[0]["name"] == "protocol.py" and rows[0]["has_map"] is False
    # A check saved before the summary file existed is still listed, from its analysis.
    folder = client.app.state.settings.data_dir / "checks" / buggy["id"]  # type: ignore[attr-defined]
    (folder / "summary.json").unlink()
    assert client.get("/api/checks").json()["checks"][1]["findings"] == rows[1]["findings"]


def test_bad_inputs_are_refused_with_a_sentence(client: TestClient) -> None:
    assert client.post("/api/checks", json={"protocol": "   "}).status_code == 422
    protocol = "def run(protocol):\n    pass\n"  # a protocol, so the plate map is what is refused
    r = client.post("/api/checks", json={"protocol": protocol, "platemap": "{not json"})
    assert r.status_code == 422 and "not JSON" in r.json()["detail"]
    r = client.post("/api/checks", json={"protocol": protocol, "platemap": {"id": "x"}})
    assert r.status_code == 422 and "not valid" in r.json()["detail"]
    assert client.get("/api/checks/nope").status_code == 404


def test_examples_and_platemaps_are_served(client: TestClient) -> None:
    example = client.get("/api/examples/protocol").json()
    assert example["protocol"] == FIXTURE.read_text()
    assert example["platemap_id"] == "pcr-01"
    maps = client.get("/api/platemaps").json()["platemaps"]
    assert {m["id"] for m in maps} >= {"pcr-01", "dil-01", "norm-01"}
    assert client.get("/api/platemaps/pcr-01").json() == json.loads(PLATEMAP.read_text())
    assert client.get("/api/platemaps/../x").status_code in (404, 422)


def test_rate_limit_counts_a_window() -> None:
    limit = RateLimit(n=2, per_s=10)
    assert limit.check("a", now=0) and limit.check("a", now=1)
    assert not limit.check("a", now=2)
    assert limit.check("b", now=2)
    assert limit.check("a", now=11)


def test_a_file_that_is_not_a_protocol_is_refused_before_the_simulator(client: TestClient) -> None:
    """Python with no run(protocol), text that is not Python, a binary: refused with a sentence.
    A protocol with a syntax error is still a protocol and goes on to the simulator."""
    from api.checks import protocol_problem

    for text in ("print('hello')\n", "a shopping list\neggs, milk\n", "\x00\x01PNG"):
        r = client.post("/api/checks", json={"protocol": text, "name": "x.py"})
        assert r.status_code == 422, text
        assert "protocol" in r.json()["detail"]
    assert protocol_problem("metadata = {'apiLevel': '2.13'}\ndef run(ctx):\n    x = (\n") is None
    assert protocol_problem("async def run(protocol):\n    pass\n") is None


def test_no_protocol_in_the_public_library_is_refused() -> None:
    """833 of 833 pass. Skipped where the library is not checked out."""
    from api.checks import protocol_problem
    from provette.corpus.library import DEFAULT_CHECKOUT, discover

    if not (DEFAULT_CHECKOUT / "protocols").is_dir():
        pytest.skip("the public library is not checked out (provette corpus fetch)")
    protocols = discover(DEFAULT_CHECKOUT)
    refused = [
        p.slug
        for p in protocols
        if protocol_problem(p.source.read_text(encoding="utf-8", errors="replace"))
    ]
    assert len(protocols) == 833 and refused == []
