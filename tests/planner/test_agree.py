"""Agreement between two plate maps: the same map, a renamed one, a wrong amount, a wrong
position, on the frozen hand-written maps."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from provette.intent.spec import platemap_from_dict
from provette.planner.agree import agree, match_liquids, probe_name

ROOT = Path(__file__).parents[2]
MAPS = ROOT / "eval" / "platemaps"


def load(request_id: str) -> dict[str, Any]:
    return json.loads((MAPS / f"{request_id}.json").read_text(encoding="utf-8"))


def test_a_map_agrees_with_itself() -> None:
    for request_id in ("pcr-01", "dil-01", "elisa-01", "cherry-01", "brad-01", "pool-01"):
        pm = platemap_from_dict(load(request_id))
        out = agree(pm, pm)
        assert out["agree"], (request_id, out)
        assert out["amounts"]["matched"] == out["amounts"]["reference_wells"]


def test_probe_names() -> None:
    pm = platemap_from_dict(load("elisa-01"))
    assert [probe_name(s) for s in pm.liquids] == ["standard 1", "serum 1"]
    assert probe_name(platemap_from_dict(load("pcr-03")).liquids[1]) == "template B3"


def test_renamed_liquids_and_regrouped_wells_still_agree() -> None:
    row = load("pcr-02")
    row["liquids"][0].update({"name": "pcr_mix", "pattern": r"(?i)mix"})
    row["liquids"][2].update({"name": "dna_{i}", "pattern": r"(?i)dna\D{0,12}?(\d+)"})
    members = row["variants"][0]["groups"][0]["members"]
    renamed = [
        {"pcr_mix": 12.5, "water": 10.5, "dna_" + next(k for k in m if k.startswith("sample_"))
         .split("_")[1]: 2}
        for m in members
    ]  # fmt: skip
    row["variants"][0]["groups"] = [
        {"name": "first half", "members": renamed[:12], "within": None, "position": "free",
         "order_hint": "index"},
        {"name": "second half", "members": renamed[12:], "within": None, "position": "free",
         "order_hint": "index"},
    ]  # fmt: skip
    out = agree(platemap_from_dict(row), platemap_from_dict(load("pcr-02")))
    assert out["liquids"]["matched"] == {"master_mix": "pcr_mix", "water": "water",
                                         "sample_{i}": "dna_{i}"}  # fmt: skip
    assert out["agree"], out


def test_a_wrong_amount_is_an_amounts_disagreement() -> None:
    row = load("pcr-01")
    row["variants"][0]["groups"][0]["members"][3]["master_mix"] = 18
    out = agree(platemap_from_dict(row), platemap_from_dict(load("pcr-01")))
    assert not out["amounts"]["agree"] and out["positions"]["agree"] and out["liquids"]["agree"]
    assert out["amounts"]["matched"] == 7
    assert out["amounts"]["unmatched_reference"] == ["20 ul master_mix + 5 ul sample_4"]
    assert out["amounts"]["unmatched_proposed"] == ["18 ul master_mix + 5 ul sample_4"]
    assert not out["agree"]


def test_within_tolerance_is_the_same_amount() -> None:
    row = load("norm-01")
    member = row["variants"][0]["groups"][0]["members"][0]
    member["sample_1"] = round(member["sample_1"], 1)
    assert agree(platemap_from_dict(row), platemap_from_dict(load("norm-01")))["agree"]


def test_pinning_free_wells_is_a_positions_disagreement_only() -> None:
    row = load("pcr-01")
    members = row["variants"][0]["groups"][0]["members"]
    row["variants"][0]["pinned"] = {f"{r}1": m for r, m in zip("ABCDEFGH", members, strict=True)}
    row["variants"][0]["groups"] = []
    out = agree(platemap_from_dict(row), platemap_from_dict(load("pcr-01")))
    assert out["amounts"]["agree"] and not out["positions"]["agree"]
    assert out["positions"]["pinned_differences"] == [
        "free in the reference; proposed pinned in <well> (x8)"
    ]


def test_a_missing_constraint_is_reported() -> None:
    row = load("elisa-01")
    row["variants"][0]["groups"][0]["position"] = "free"
    out = agree(platemap_from_dict(row), platemap_from_dict(load("elisa-01")))
    assert out["amounts"]["agree"] and not out["positions"]["agree"]
    assert out["positions"]["constraint_differences"] == [
        "100 ul serum_N: free proposed, same_as_source expected (x40)"
    ]


def test_the_best_of_many_reference_variants_is_taken() -> None:
    reference = platemap_from_dict(load("dil-01"))
    row = load("dil-01")
    row["variants"] = [copy.deepcopy(next(v for v in row["variants"] if v["name"].startswith(
        "row C; first point is neat")))]  # fmt: skip
    out = agree(platemap_from_dict(row), reference)
    assert out["agree"] and out["best_pair"]["reference"].startswith("row C; first point is neat")
    assert out["variants"] == {"proposed": 1, "reference": 32}


def test_a_role_difference_is_reported_but_the_amounts_still_compare() -> None:
    row = load("dil-03")
    row["liquids"][1].update({"name": "bsa_stock", "role": "sample"})
    for variant in row["variants"]:
        for member in variant["groups"][0]["members"]:
            member["bsa_stock"] = member.pop("bsa")
    out = agree(platemap_from_dict(row), platemap_from_dict(load("dil-03")))
    assert out["liquids"]["matched"] == {"water": "water", "bsa": "bsa_stock"}
    assert out["liquids"]["differences"] == [
        "bsa: role 'sample' proposed (bsa_stock), 'reagent' expected"
    ]
    assert not out["liquids"]["agree"] and out["amounts"]["agree"] and not out["agree"]


def test_pinned_count_must_match_even_when_no_well_matched() -> None:
    row = load("pcr-01")
    row["variants"][0]["groups"][0]["members"] = [{"master_mix": 1, f"sample_{i}": 1}
                                                  for i in range(1, 9)]  # fmt: skip
    reference = load("pcr-03")
    out = agree(platemap_from_dict(row), platemap_from_dict(reference))
    assert out["amounts"]["matched"] == 0 and not out["positions"]["agree"]


def test_an_unmatched_liquid_is_named() -> None:
    row = load("pcr-01")
    row["liquids"].append({"name": "oil", "role": "reagent", "bind": "name", "pattern": "oil"})
    row["variants"][0]["groups"][0]["members"][0]["oil"] = 5
    out = agree(platemap_from_dict(row), platemap_from_dict(load("pcr-01")))
    assert out["liquids"]["unmatched_proposed"] == ["oil"] and not out["liquids"]["agree"]
    assert not out["amounts"]["agree"]
    assert (
        match_liquids(platemap_from_dict(row), platemap_from_dict(load("pcr-01")))[
            "unmatched_reference"
        ]
        == []
    )
