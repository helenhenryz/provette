"""The planner's tools on hand-built input: the proposal's validation path, the number rule,
the calculators' shape. No network."""

from __future__ import annotations

import json
from typing import Any

import pytest

from provette.planner.tools import SCHEMAS, TOOL_NAMES, Toolbox, loads_closing_brackets

REQUEST = (
    "Set up PCR reactions for 8 DNA samples in a 96-well PCR plate. Each reaction is 20 ul of "
    "master mix plus 5 ul of sample."
)


def pcr_map(volume: float = 20) -> dict[str, Any]:
    return {
        "liquids": [
            {"name": "master_mix", "role": "reagent", "bind": "name", "pattern": "(?i)master"},
            {
                "name": "sample_{i}",
                "role": "sample",
                "bind": "indexed",
                "pattern": r"(?i)sample\D{0,12}?(\d+)",
                "count": 8,
                "index": "number",
            },
        ],
        "destination": {"select": "auto"},
        "variants": [
            {
                "name": "8 reactions",
                "why": "the request does not say which wells",
                "pinned": {},
                "groups": [
                    {
                        "name": "reactions",
                        "members": [{"master_mix": volume, f"sample_{i}": 5} for i in range(1, 9)],
                        "within": None,
                        "position": "free",
                        "order_hint": "index",
                    }
                ],
            }
        ],
        "discard_intended": [],
        "notes": [],
    }


def test_schemas_name_the_five_tools() -> None:
    assert TOOL_NAMES == ("labware", "dilution_series", "normalise", "master_mix",
                          "propose_platemap")  # fmt: skip
    for schema in SCHEMAS:
        assert schema["function"]["parameters"]["type"] == "object"


def test_a_valid_map_is_accepted_and_carries_the_id_and_request() -> None:
    box = Toolbox("pcr-01", REQUEST)
    out = box.call("propose_platemap", {"platemap": pcr_map()})
    assert out["accepted"] is True and out["liquids"] == 2 and out["variants"] == 1
    assert box.proposed is not None
    assert box.proposed.id == "pcr-01" and box.proposed.request == REQUEST
    assert box.proposed.variants[0].groups[0].members[2] == {"master_mix": 20, "sample_3": 5}
    assert box.rejections == []


def test_the_map_may_arrive_as_a_json_string() -> None:
    box = Toolbox("pcr-01", REQUEST)
    out = box.call("propose_platemap", json.dumps({"platemap": json.dumps(pcr_map())}))
    assert out["accepted"] is True


def test_a_string_missing_the_bracket_that_closes_variants_is_repaired_and_said() -> None:
    # the slip Nemotron makes: `...}]}` then `, "discard_intended"` without the `]` of variants
    text = json.dumps(pcr_map())
    broken = text.replace('}]}], "discard_intended"', '}]}, "discard_intended"')
    assert broken != text
    box = Toolbox("pcr-01", REQUEST)
    out = box.call("propose_platemap", {"platemap": broken})
    assert out["accepted"] is True and out["repaired"].startswith("inserted ']' at character")
    assert box.proposed is not None and box.repairs == [out["repaired"]] and box.rejections == []
    with pytest.raises(json.JSONDecodeError):
        loads_closing_brackets('{"a": [1, 2}, "b": 3')  # a wrong bracket, not a missing one
    with pytest.raises(json.JSONDecodeError):
        loads_closing_brackets('{"members": [{"x": 50}] * 48}')
    fixed, how = loads_closing_brackets('{"a": [1, 2, "b": 3}')
    assert fixed == {"a": [1, 2], "b": 3} and how == "inserted ']' at character 11"


def test_an_invalid_map_comes_back_with_the_validation_error() -> None:
    box = Toolbox("pcr-01", REQUEST)
    bad = pcr_map()
    bad["variants"][0]["groups"][0]["members"][0] = {"master_mix": 20, "sample_9": 5}
    out = box.call("propose_platemap", {"platemap": bad})
    assert out["accepted"] is False and "'sample_9' is outside 1..8" in out["error"]
    assert box.proposed is None and len(box.rejections) == 1
    missing = pcr_map()
    del missing["liquids"]
    out = box.call("propose_platemap", {"platemap": missing})
    assert out["accepted"] is False and "missing or misnames a field" in out["error"]
    out = box.call("propose_platemap", {"platemap": {"liquids": [], "variants": "no"}})
    assert out["accepted"] is False
    out = box.call("propose_platemap", {"platemap": "{not json"})
    assert out["accepted"] is False and "not valid JSON" in out["error"]
    assert box.proposed is None and len(box.rejections) == 4


def test_a_volume_the_model_was_never_given_is_refused() -> None:
    box = Toolbox("pcr-01", REQUEST)
    out = box.call("propose_platemap", {"platemap": pcr_map(volume=22)})
    assert out["accepted"] is False
    assert "22 ul of master_mix" in out["error"] and "never computed" in out["error"]
    assert box.proposed is None
    # a number from a calculator result is allowed
    box.call("master_mix", {"components": {"mix": 22}, "reactions": 8})
    assert box.call("propose_platemap", {"platemap": pcr_map(volume=22)})["accepted"] is True


def test_declared_amounts_need_no_number() -> None:
    box = Toolbox("x", "Add 250 ul of reagent to the standards already in the plate.")
    row = pcr_map()
    row["liquids"][0]["name"] = "reagent"
    row["liquids"][0]["pattern"] = "(?i)reagent"
    row["variants"][0]["groups"][0]["members"] = [
        {"reagent": 250, f"sample_{i}": "declared"} for i in range(1, 9)
    ]
    assert box.call("propose_platemap", {"platemap": row})["accepted"] is True


def test_dilution_series_gives_what_each_well_ends_holding_split_in_two() -> None:
    box = Toolbox("dil", "a 1:2 series, 100 ul per well")
    out = box.call(
        "dilution_series",
        {"stock_concentration": 1, "points": 3, "factor": 2, "final_volume_ul": 100,
         "first_point_is_stock": False},
    )  # fmt: skip
    assert [w["of_which_stock_ul"] for w in out["wells"]] == [50, 25, 12.5]
    assert [w["of_which_diluent_ul"] for w in out["wells"]] == [50, 75, 87.5]
    assert out["reading"]["last_well_holds_ul"] == 100
    kept = box.call(
        "dilution_series",
        {"stock_concentration": 1, "points": 3, "factor": 2, "final_volume_ul": 100,
         "first_point_is_stock": True, "remove_excess": False},
    )  # fmt: skip
    assert kept["wells"][0] == {"point": 1, "dilution": "1:1", "ends_holding_ul": 100,
                                "of_which_stock_ul": 100, "of_which_diluent_ul": 0}  # fmt: skip
    assert kept["wells"][2] == {"point": 3, "dilution": "1:4", "ends_holding_ul": 200,
                                "of_which_stock_ul": 50, "of_which_diluent_ul": 150}  # fmt: skip
    assert kept["reading"]["last_well_holds_ul"] == 200
    assert {50.0, 87.5, 200.0} <= box.numbers


def test_normalise_and_master_mix_shapes() -> None:
    box = Toolbox("n", "normalise to 10 ng/ul in 50 ul")
    out = box.call("normalise", {"concentrations": [85, 25], "target": 10, "final_volume_ul": 50})
    assert out["samples"][0]["sample_ul"] == 5.8824 and out["samples"][0]["diluent_ul"] == 44.1176
    assert out["samples"][1]["sample_ul"] == 20 and "warning" not in out["samples"][1]
    mix = box.call("master_mix", {"components": {"buffer": 10, "taq": 0.5}, "reactions": 12})
    assert mix["dispense_per_reaction_ul"] == 10.5 and mix["total_pooled_ul"] == 138.6


def test_labware_lists_wells_and_volumes() -> None:
    out = Toolbox("l", "").call("labware", {"kind": "tubes"})
    assert out["labware"][0]["well_names"].startswith("A1..D6")
    assert "kind must be one of" in Toolbox("l", "").call("labware", {"kind": "spoon"})["error"]


@pytest.mark.parametrize(
    ("name", "arguments", "fragment"),
    [
        ("teleport", {}, "no tool named 'teleport'"),
        ("labware", "{kind: plate", "not valid JSON"),
        ("labware", {"kinds": "plate"}, "wrong arguments for labware"),
        ("dilution_series", {"stock_concentration": 1, "points": 0, "factor": 2,
                             "final_volume_ul": 100, "first_point_is_stock": True},
         "at least one point"),
    ],
)  # fmt: skip
def test_bad_calls_come_back_as_errors(name: str, arguments: Any, fragment: str) -> None:
    assert fragment in Toolbox("x", "").call(name, arguments)["error"]


def test_the_technique_is_copied_into_the_map_when_the_caller_has_one() -> None:
    box = Toolbox("pcr-01", REQUEST, "PCR setup")
    assert box.call("propose_platemap", {"platemap": pcr_map()})["accepted"] is True
    assert box.proposed is not None and box.proposed.technique == "PCR setup"
    plain = Toolbox("pcr-01", REQUEST)
    plain.call("propose_platemap", {"platemap": pcr_map()})
    assert plain.proposed is not None and plain.proposed.technique is None


def test_a_liquid_whose_name_its_own_pattern_misses_is_refused_for_repair() -> None:
    """Seen live: the planner named the reagent 'bradford' with the pattern 'bradford reagent'.
    The map passed, and the run stopped the moment it started, because the writer declares each
    liquid by its name and the map could not then find it. Refused here, so the planner repairs."""
    box = Toolbox("pcr-01", REQUEST)
    bad = pcr_map()
    bad["liquids"][0] = {"name": "mix", "role": "reagent", "bind": "name", "pattern": "(?i)master"}
    for member in bad["variants"][0]["groups"][0]["members"]:
        member["mix"] = member.pop("master_mix")
    out = box.call("propose_platemap", {"platemap": bad})
    assert out["accepted"] is False and box.proposed is None
    assert "'mix' does not match" in out["error"] and "rename the liquid" in out["error"]
    assert box.call("propose_platemap", {"platemap": pcr_map()})["accepted"] is True  # repaired
