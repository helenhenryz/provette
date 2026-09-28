"""LABWARE-FOR-TECHNIQUE: the six fixture protocols under tests/fixtures/intent/labware/, each
with its own plate map, through the real simulator; and the table and classifier without it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provette.cli import main
from provette.intent import load_platemap
from provette.intent.cli import verify
from provette.intent.labware import TECHNIQUES, labware_class, need_of
from provette.intent.report import Verification, report_json, report_text
from provette.intent.spec import dump_platemap, platemap_from_dict

FIXTURES = Path(__file__).parents[1] / "fixtures" / "intent"
LABWARE = FIXTURES / "labware"

_cache: dict[str, Verification] = {}


def verified(name: str) -> Verification:
    if name not in _cache:
        _cache[name] = verify(LABWARE / f"{name}.py", load_platemap(LABWARE / f"{name}.json"))
    return _cache[name]


# -- the table and the classifier (no simulator) ----------------------------------------------


def test_the_classifier_reads_load_names() -> None:
    assert labware_class("nest_96_wellplate_100ul_pcr_full_skirt") == "pcr"
    assert labware_class("biorad_96_wellplate_200ul_pcr") == "pcr"
    assert labware_class("opentrons_96_aluminumblock_generic_pcr_strip_200ul") == "pcr"
    assert labware_class("nest_96_wellplate_200ul_flat") == "flat"
    assert labware_class("corning_96_wellplate_360ul_flat") == "flat"
    assert labware_class("nest_96_wellplate_2ml_deep") == "deep"
    assert labware_class("nest_12_reservoir_15ml") == "reservoir"
    assert labware_class("nest_1_reservoir_195ml") == "reservoir"
    assert labware_class("opentrons_24_tuberack_nest_1.5ml_snapcap") == "tubes"
    assert labware_class("opentrons_15_tuberack_falcon_15ml_conical") == "tubes"
    # a name that says nothing is unclassed, and the check is silent on it
    assert labware_class("opentrons_96_aluminumblock_nest_wellplate_100ul") is None
    assert labware_class("my_lab_custom_96_plate") is None


def test_the_table_covers_every_technique_word_of_the_request_sets() -> None:
    root = Path(__file__).parents[2] / "eval"
    words = set()
    for path in (root / "requests" / "requests.jsonl", root / "requests-hard" / "requests.jsonl"):
        words |= {json.loads(line)["technique"] for line in path.read_text().splitlines() if line}
    assert words <= set(TECHNIQUES), words - set(TECHNIQUES)
    assert need_of("pcr setup") is need_of("PCR setup")  # matched without case
    assert need_of("PCR setup").destination == ("pcr",)  # type: ignore[union-attr]
    assert need_of("Protein assay").destination == ("flat", "deep")  # type: ignore[union-attr]
    assert need_of("Cherrypicking").destination is None  # type: ignore[union-attr]
    assert need_of("Knitting") is None and need_of(None) is None


def test_technique_is_optional_on_the_map_and_round_trips() -> None:
    without = load_platemap(FIXTURES / "pcr4.json")
    assert without.technique is None
    assert "technique" not in dump_platemap(without)
    row = json.loads((LABWARE / "near_miss_pcr_in_pcr_plate.json").read_text())
    with_it = platemap_from_dict(row)
    assert with_it.technique == "PCR setup"
    assert platemap_from_dict(dump_platemap(with_it)) == with_it
    assert platemap_from_dict({**row, "technique": "  "}).technique is None
    assert platemap_from_dict({**row, "technique": None}).technique is None


# -- the fixtures (simulator) ------------------------------------------------------------------


@pytest.mark.sim
def test_colony_pcr_in_a_flat_plate_is_a_warning() -> None:
    result = verified("fires_colony_pcr_in_flat_plate")
    assert result.intent.status == "verified"  # every well holds what the map says
    assert [f.severity for f in result.labware] == ["warning"]
    finding = result.labware[0]
    assert finding.rule_id == "LABWARE-FOR-TECHNIQUE" and finding.certain
    assert "PCR setup" in finding.explanation
    assert "PCR plate" in finding.explanation  # the label the author gave
    assert "nest_96_wellplate_200ul_flat" in finding.explanation
    assert "thermocycler" in finding.explanation
    assert finding.line is not None and "dispense" in result.source_lines[finding.line - 1]
    assert {w.well for w in finding.wells} == {f"{row}1" for row in "ABCDEFGH"}
    assert finding.fingerprint and finding.sources
    assert result.exit_code == 1


@pytest.mark.sim
def test_elisa_in_a_pcr_plate_is_a_warning() -> None:
    result = verified("fires_elisa_in_pcr_plate")
    assert result.intent.status == "verified"
    assert [f.severity for f in result.labware] == ["warning"]
    finding = result.labware[0]
    assert "ELISA" in finding.explanation and "ELISA plate" in finding.explanation
    assert "nest_96_wellplate_100ul_pcr_full_skirt" in finding.explanation
    assert "coated" in finding.explanation
    assert result.exit_code == 1


@pytest.mark.sim
def test_an_enzyme_declared_in_a_reservoir_is_a_note_and_nothing_else() -> None:
    result = verified("fires_enzyme_declared_in_reservoir")
    assert result.intent.status == "verified"
    assert [f.severity for f in result.labware] == ["note"]
    finding = result.labware[0]
    assert finding.roles_basis == "declared" and finding.tier == "role"
    assert "restriction enzyme" in finding.title
    assert finding.line is not None
    assert 'trough["A3"].load_liquid(enzyme' in result.source_lines[finding.line - 1]
    assert [w.well for w in finding.wells] == ["A3"]  # not the water in A1, not the buffer in A2
    assert "Cloning" in finding.explanation and "mm deep" in finding.explanation
    assert result.exit_code == 0  # a note does not fail verify


@pytest.mark.sim
@pytest.mark.parametrize(
    "name",
    [
        "near_miss_pcr_in_pcr_plate",
        "near_miss_bradford_in_corning_flat",
        "near_miss_cherrypick_any_plate",
    ],
)
def test_the_near_misses_are_silent(name: str) -> None:
    result = verified(name)
    assert result.intent.status == "verified"
    assert result.labware == ()
    assert result.exit_code == 0


@pytest.mark.sim
def test_a_map_without_a_technique_verifies_as_before() -> None:
    result = verify(FIXTURES / "correct.py", load_platemap(FIXTURES / "pcr4.json"))
    assert result.platemap.technique is None
    assert result.labware == () and result.exit_code == 0
    text = report_text(result)
    assert "Labware for the technique" not in text
    data = report_json(result)
    assert data["labware"] == [] and data["technique"] is None


@pytest.mark.sim
def test_the_reports_carry_the_findings(capsys: pytest.CaptureFixture[str]) -> None:
    result = verified("fires_colony_pcr_in_flat_plate")
    text = report_text(result)
    assert "Labware for the technique (PCR setup): 1 finding." in text
    assert "1. WARNING LABWARE-FOR-TECHNIQUE:" in text
    assert "   Fix: Load nest_96_wellplate_100ul_pcr_full_skirt" in text
    assert "   Source: Opentrons, module setup" in text
    data = report_json(result)
    assert data["technique"] == "PCR setup" and data["exit_code"] == 1
    assert [f["rule_id"] for f in data["labware"]] == ["LABWARE-FOR-TECHNIQUE"]
    assert data["labware"][0]["fingerprint"] == result.labware[0].fingerprint

    silent = report_text(verified("near_miss_pcr_in_pcr_plate"))
    assert "Labware for the technique (PCR setup): nothing to flag." in silent

    code = main(
        [
            "verify",
            str(LABWARE / "fires_colony_pcr_in_flat_plate.py"),
            "--platemap",
            str(LABWARE / "fires_colony_pcr_in_flat_plate.json"),
        ]
    )
    assert code == 1 and "LABWARE-FOR-TECHNIQUE" in capsys.readouterr().out
