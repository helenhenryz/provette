"""Every tool's implementation, on the frozen plate maps and (for the checks) a fixture protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from provette.agent.local_runner import LocalRunner
from provette.agent.tools import SCHEMAS, TOOL_NAMES, Toolbox, checks_for_model, liquid_names

ROOT = Path(__file__).parents[2]
MAPS = ROOT / "eval" / "platemaps"
PCR_BUGGY = ROOT / "tests" / "fixtures" / "protocols" / "pcr_buggy.py"


class NoRunner:
    """For the tools that never run the checks."""

    name = "none"

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("this test must not run the checks")

    def close(self) -> None:
        pass


class FakeRunner:
    """Says what it is told; records what it was given."""

    name = "fake"

    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.seen: list[str] = []

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        self.seen.append(protocol_text)
        return dict(self.result)

    def close(self) -> None:
        pass


CLEAN = {"simulator": "passed", "verify_exit": 0, "verify_text": "ok", "check_exit": 0,
         "check_text": "clean", "findings": [], "seconds": 1.0}  # fmt: skip


def load(map_id: str) -> dict[str, Any]:
    return json.loads((MAPS / f"{map_id}.json").read_text())


def test_schemas_name_every_tool_once() -> None:
    assert TOOL_NAMES == (
        "platemap",
        "labware",
        "dilution_series",
        "normalise",
        "master_mix",
        "write_protocol",
        "submit",
    )  # fmt: skip  (run_checks is callable but no longer offered: write_protocol checks)
    for schema in SCHEMAS:
        function = schema["function"]
        assert schema["type"] == "function" and len(function["description"]) > 80
        assert function["parameters"]["type"] == "object"
        assert hasattr(Toolbox, f"tool_{function['name']}")


def test_liquid_names_match_e4() -> None:
    assert liquid_names(load("pcr-01")) == ["master mix"] + [f"sample {i}" for i in range(1, 9)]
    assert liquid_names(load("dil-01")) == ["pbs", "drug"]
    assert liquid_names(load("pcr-06"))[1:3] == ["colony 1", "colony 2"]
    assert liquid_names(load("cherry-01")) == []


@pytest.mark.parametrize("map_id", [p.stem for p in sorted(MAPS.glob("*.json"))])
def test_platemap_tool_on_every_map(map_id: str, tmp_path: Path) -> None:
    out = Toolbox(load(map_id), NoRunner(), tmp_path).call("platemap", "{}")
    json.dumps(out)  # serialisable
    assert out["id"] == map_id and "wells" in out or "groups" in out
    assert len(json.dumps(out)) < 4000, "the plate map must stay compact for a small model"


def test_platemap_tool_reads_pinned_wells_and_groups(tmp_path: Path) -> None:
    dil = Toolbox(load("dil-01"), NoRunner(), tmp_path).call("platemap", "{}")
    assert dil["wells"]["A1"] == "50 ul drug + 50 ul pbs"
    assert dil["wells"]["A12"] == "0.02 ul drug + 99.98 ul pbs"
    assert "32 ways" in dil["readings"]
    pcr = Toolbox(load("pcr-04"), NoRunner(), tmp_path).call("platemap", "{}")
    group = pcr["groups"][0]
    assert group["wells"] == 18 and group["each_holds"] == "8 ul master mix + 2 ul sample"
    assert group["samples"] == "sample 1 to sample 6, each in 3 wells"
    full = Toolbox(load("pcr-03"), NoRunner(), tmp_path).call("platemap", "{}")
    assert full["wells"]["every_well"].startswith("A1 to H12 (96 wells")
    assert "same-named well" in full["wells"]["each_holds"]
    brad = Toolbox(load("brad-01"), NoRunner(), tmp_path).call("platemap", "{}")
    assert brad["groups"][1]["each_holds"].startswith("all of the standard already in the well")
    elisa = Toolbox(load("elisa-01"), NoRunner(), tmp_path).call("platemap", "{}")
    assert "elisa|coated|assay" in elisa["destination"]
    assert elisa["groups"][1]["where"] == "any of A12..H12 (8 wells)"


def test_labware_tool_reads_the_installed_definitions(tmp_path: Path) -> None:
    box = Toolbox(load("pcr-01"), NoRunner(), tmp_path)
    plates = box.call("labware", '{"kind": "plate"}')["labware"]
    by_name = {p["load_name"]: p for p in plates}
    assert by_name["nest_96_wellplate_100ul_pcr_full_skirt"]["max_ul_per_well"] == 100
    assert by_name["corning_384_wellplate_112ul_flat"]["wells"] == 384
    assert by_name["nest_96_wellplate_2ml_deep"]["well_names"] == "A1..H12 (8 rows x 12 columns)"
    tips = box.call("labware", '{"kind": "tips"}')["labware"]
    assert {t["tip_ul"] for t in tips} == {20, 200, 300, 1000}
    tubes = box.call("labware", '{"kind": "tubes"}')["labware"]
    mixed = next(t for t in tubes if t["load_name"].startswith("opentrons_10_"))
    assert set(mixed["max_ul_per_well"]) == {"15000 ul", "50000 ul"}
    blocks = box.call("labware", '{"kind": "module_block"}')
    assert "temperature module gen2" in blocks["modules"]
    assert "kind must be one of" in box.call("labware", '{"kind": "pipette"}')["error"]


def test_arithmetic_tools_round_for_the_model(tmp_path: Path) -> None:
    box = Toolbox(load("dil-01"), NoRunner(), tmp_path)
    series = box.call(
        "dilution_series",
        {
            "stock_concentration": 1,
            "points": 12,
            "factor": 2,
            "final_volume_ul": 100,
            "first_point_is_stock": False,
        },  # fmt: skip
    )
    assert series["wells"][0] == {
        "well": 1, "step_1_add_diluent_ul": 100.0, "step_2_transfer_in_ul": 100.0,
        "from": "stock", "step_3": "mix", "then_holds_ul": 200.0, "ends_holding_ul": 100.0,
        "of_which_stock_ul": 50.0, "concentration": 0.5, "dilution": "1:2",
    }  # fmt: skip
    assert series["wells"][1]["from"] == "well 1"
    assert series["wells"][11]["of_which_stock_ul"] == 0.02
    assert series["last_well_remove_to_waste_ul"] == 100 and "only move" in series["how"]
    assert series["stock_needed_ul"] == 100 and series["diluent_needed_ul"] == 1200
    norm = box.call("normalise", {"concentrations": [85, 210], "target": 10, "final_volume_ul": 50})
    assert norm["samples"][0]["sample_ul"] == 5.88 and norm["samples"][1]["diluent_ul"] == 47.62
    mix = box.call("master_mix", {"components": {"buffer": 10, "enzyme": 0.5}, "reactions": 12})
    assert mix["dispense_per_reaction_ul"] == 10.5 and mix["total_pooled_ul"] == 138.6


def test_call_never_raises_on_what_the_model_sends(tmp_path: Path) -> None:
    box = Toolbox(load("dil-01"), NoRunner(), tmp_path)
    assert "no tool named" in box.call("labwar", "{}")["error"]
    assert "not valid JSON" in box.call("labware", "{kind: plate}")["error"]
    assert "wrong arguments" in box.call("labware", '{"knd": "plate"}')["error"]
    assert "must be a JSON object" in box.call("labware", "[1]")["error"]
    nonsense = ('{"stock_concentration": 1, "points": 0, "factor": 2, "final_volume_ul": 100, '
                '"first_point_is_stock": true}')  # fmt: skip
    assert "error" in box.call("dilution_series", nonsense)
    assert "error" in box.call("write_protocol", '{"text": "   "}')
    assert box.call("run_checks", None)["ready_to_submit"] is False


def test_write_protocol_stores_numbered_drafts_and_flags_syntax(tmp_path: Path) -> None:
    box = Toolbox(load("pcr-01"), FakeRunner(CLEAN), tmp_path)
    first = box.call("write_protocol", {"text": "def run(protocol):\n    pass"})
    assert first["stored"] and first["draft"] == 0 and first["lines"] == 2
    assert first["checks"]["ready_to_submit"] is True and "submit" in first["next"]
    assert (tmp_path / "00-draft.py").read_text() == "def run(protocol):\n    pass\n"
    second = box.call("write_protocol", {"text": "def run(protocol)\n    pass\n"})
    assert second["draft"] == 1 and second["syntax_error"].startswith("line 1:")
    assert (tmp_path / "01-draft.py").exists()


def test_run_checks_and_submit_bookkeeping(tmp_path: Path) -> None:
    finding = {"rule_id": "R", "severity": "warning", "line": 3, "title": "t", "fix": "f",
               "explanation": "long"}  # fmt: skip
    runner = FakeRunner({**CLEAN, "verify_exit": 1, "verify_text": "x" * 7000, "check_exit": 1,
                         "findings": [finding]})  # fmt: skip
    box = Toolbox(load("pcr-01"), runner, tmp_path)
    shown = box.call("write_protocol", {"text": "x = 1\n"})["checks"]  # write checks the draft
    assert shown["ready_to_submit"] is False and shown["verdict"].startswith("Not ready")
    assert shown["verify_report"].endswith("[... cut here ...]") and "truncated" in shown
    assert shown["findings"] == [{"rule_id": "R", "severity": "warning", "line": 3, "title": "t",
                                  "fix": "f"}]  # fmt: skip
    saved = json.loads((tmp_path / "00-checks.json").read_text())
    assert saved["verify_text"] == "x" * 7000 and saved["draft"] == 0  # untruncated on disk
    assert runner.seen == ["x = 1\n"]
    early = box.call("submit", "{}")
    assert early["verified_and_clean_at_last_check"] is False
    assert early["note"] == "submitted with problems still reported"

    runner.result = dict(CLEAN)
    written = box.call("write_protocol", {"text": "x = 2\n"})  # checked on the spot
    assert written["checks"]["ready_to_submit"] is True
    assert box.call("submit", "{}")["verified_and_clean_at_last_check"] is True
    assert runner.seen == ["x = 1\n", "x = 2\n"]
    assert len(box.check_results) == 2


def test_rejected_draft_names_the_real_labware_when_one_was_invented() -> None:
    error = 'line 10: FileNotFoundError: Labware "opentrons_96_tiprack_200ul" not found with v'
    shown = checks_for_model({"simulator": "rejected", "simulator_error": error, "draft": 0})
    assert shown["hint"].startswith("There is no labware called 'opentrons_96_tiprack_200ul'.")
    assert "opentrons_96_filtertiprack_200ul" in shown["hint"]
    shown = checks_for_model({"simulator": "rejected", "draft": 0,
                              "simulator_error": "line 33: KeyError [line 33]: 'A7'"})  # fmt: skip
    assert shown["hint"].startswith("'A7' is not a well of the labware used at that line.")
    assert "A1..D6 (4 rows x 6 columns): opentrons_24_tuberack_nest_1.5ml_snapcap" in shown["hint"]
    shown = checks_for_model({"simulator": "rejected", "draft": 0,
                              "simulator_error": "line 17: AttributeError [line 17]: 'str' object "
                              "has no attribute '_id'"})  # fmt: skip
    assert shown["hint"].startswith("load_liquid was given a name string.")
    shown = checks_for_model({"simulator": "rejected", "draft": 0,
                              "simulator_error": "line 46: FailedToPlanMoveError: Arc out of "
                              "bounds in the Z-axis"})  # fmt: skip
    assert "aluminium blocks" in shown["hint"] and "never a tube rack" in shown["hint"]


def test_an_invented_keyword_is_named_with_the_api_call_not_the_tracer() -> None:
    # e5 short-on-tips/dil-01: twenty drafts on `ribbon=`, because the error named the wrapper
    error = ("line 21: TypeError [line 21]: _install.<locals>.load_liquid() got an unexpected "
             "keyword argument 'ribbon'")  # fmt: skip
    shown = checks_for_model({"simulator": "rejected", "simulator_error": error, "draft": 0})
    assert shown["hint"].startswith("load_liquid() takes only the arguments the Opentrons API")
    assert "_install" not in shown["hint"] and "<locals>" not in shown["hint"]
    assert "'ribbon' is not one of them. load_liquid takes (liquid, volume)." in shown["hint"]
    assert shown["hint"].endswith("Drop the ribbon=... argument from that call.")
    other = "line 9: TypeError [line 9]: transfer() got an unexpected keyword argument 'speed'"
    shown = checks_for_model({"simulator": "rejected", "simulator_error": other, "draft": 0})
    assert shown["hint"].startswith("transfer() takes only") and "'speed'" in shown["hint"]
    assert "load_liquid" not in shown["hint"]


def test_rejected_draft_is_shown_with_the_error_only() -> None:
    shown = checks_for_model({"simulator": "rejected", "simulator_error": "line 4: no", "draft": 2})
    assert shown == {
        "draft": 2, "simulator": "rejected", "simulator_error": "line 4: no", "verify_exit": 2,
        "ready_to_submit": False,
        "verdict": "The simulator rejected the file, so nothing else was checked. Fix the "
        "error at the line named, then call write_protocol with the whole file: it checks the "
        "draft.",
    }  # fmt: skip


@pytest.mark.sim
def test_run_checks_with_the_local_runner_on_pcr_buggy(tmp_path: Path) -> None:
    box = Toolbox(load("pcr-01"), LocalRunner(), tmp_path)
    box.call("write_protocol", {"text": PCR_BUGGY.read_text()})
    shown = box.call("run_checks", "{}")
    assert shown["simulator"] == "passed"
    assert shown["verify_exit"] == 1  # 20 ul of sample where the map says 5, 40 of mix for 20
    assert shown["check_exit"] == 1 and shown["ready_to_submit"] is False
    assert {f["rule_id"] for f in shown["findings"]} >= {"CONTAM-STOCK"}
    assert "MISMATCH against plate map pcr-01" in shown["verify_report"]
    saved = json.loads((tmp_path / "00-checks.json").read_text())
    assert saved["verify"]["intent"]["status"] == "mismatch"


def test_the_same_simulator_error_three_times_says_stuck(tmp_path: Path) -> None:
    rejected = {"simulator": "rejected", "simulator_error": "line 12: KeyError [line 12]: 'E1'",
                "verify_exit": 2}  # fmt: skip
    runner = FakeRunner(rejected)
    box = Toolbox(load("pcr-01"), runner, tmp_path)
    first = box.call("write_protocol", {"text": "x = 1\n"})["checks"]
    assert "stuck" not in first
    runner.result = {**rejected, "simulator_error": "line 15: KeyError [line 15]: 'E1'"}
    second = box.call("write_protocol", {"text": "x = 2\n"})["checks"]
    assert "stuck" not in second
    third = box.call("write_protocol", {"text": "x = 3\n"})["checks"]
    assert third["stuck"].startswith("This is the same simulator error 3 times in a row.")
    runner.result = {**rejected, "simulator_error": "line 15: TipAttachedError: no"}
    assert "stuck" not in box.call("write_protocol", {"text": "x = 4\n"})["checks"]


def test_platemap_tool_shows_the_technique_as_one_line(tmp_path: Path) -> None:
    pcr = Toolbox(load("pcr-01"), NoRunner(), tmp_path).call("platemap", "{}")
    assert pcr["technique"] == (
        "PCR setup: the destination must be a PCR plate or PCR strips (the checks flag any "
        "other kind)"
    )
    cherry = Toolbox(load("cherry-01"), NoRunner(), tmp_path).call("platemap", "{}")
    assert cherry["technique"] == "Cherrypicking"  # no plate class is asked of it
    without = {k: v for k, v in load("pcr-01").items() if k != "technique"}
    assert "technique" not in Toolbox(without, NoRunner(), tmp_path).call("platemap", "{}")


def test_a_submit_the_checks_reject_is_refused_until_the_minimum_drafts(tmp_path: Path) -> None:
    # The live flow's setting (D-32): a first failing draft is sent back, not taken.
    runner = FakeRunner({**CLEAN, "verify_exit": 1})
    box = Toolbox(load("pcr-01"), runner, tmp_path, min_drafts=3)
    box.call("write_protocol", {"text": "x = 1\n"})
    refused = box.call("submit", "{}")
    assert refused["submitted"] is False and refused["refused"].startswith("Not submitted")
    assert box.submitted is False
    box.call("write_protocol", {"text": "x = 2\n"})
    assert box.call("submit", "{}")["submitted"] is False
    box.call("write_protocol", {"text": "x = 3\n"})  # the third draft: giving up is allowed
    taken = box.call("submit", "{}")
    assert taken["submitted"] is True and taken["note"] == "submitted with problems still reported"
    # a clean draft is taken at once, whatever the minimum
    runner.result = dict(CLEAN)
    fresh = Toolbox(load("pcr-01"), runner, tmp_path / "b", min_drafts=3)
    (tmp_path / "b").mkdir()
    fresh.call("write_protocol", {"text": "y = 1\n"})
    assert fresh.call("submit", "{}")["verified_and_clean_at_last_check"] is True
