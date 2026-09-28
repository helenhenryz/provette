from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from provette.corpus.library import (
    LIBRARY_COMMIT,
    discover,
    fetch,
    normalise_category,
    parse_api_level,
    parse_categories,
    tip_reuse_parameters,
)


def test_discover_reads_one_folder(make_folder: Callable[..., Path]) -> None:
    checkout = make_folder("abc123", labware_dir="custom_labware", markers=(".hide-from-search",))
    [protocol] = discover(checkout)
    assert protocol.slug == "abc123"
    assert protocol.source.name == "abc123.ot2.apiv2.py"
    assert protocol.fields_json is not None and protocol.fields_json.name == "fields.json"
    assert protocol.labware_dir is not None and protocol.labware_dir.name == "custom_labware"
    assert protocol.api_level == "2.13"
    assert protocol.categories == ["PCR"]
    assert protocol.subcategories == ["qPCR Setup"]
    assert protocol.raw_categories == ["PCR", "qpcr setup"]
    assert protocol.hidden and not protocol.ignored


def test_discover_bare_folder_and_sorting(make_folder: Callable[..., Path]) -> None:
    make_folder("zeta", fields=None, readme=None, markers=(".ignore",))
    checkout = make_folder("alpha")
    (checkout / "protocols" / "empty").mkdir()  # no .py: not a protocol
    alpha, zeta = discover(checkout)
    assert (alpha.slug, zeta.slug) == ("alpha", "zeta")
    assert zeta.fields_json is None and zeta.labware_dir is None
    assert zeta.categories == [] and zeta.raw_categories == []
    assert zeta.ignored and not zeta.hidden


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("metadata = {'apiLevel': '2.9'}", "2.9"),
        ('requirements = {"robotType": "OT-2", "apiLevel" : "2.15"}', "2.15"),
        ("metadata = {'protocolName': 'x'}", None),
    ],
)
def test_parse_api_level(source: str, expected: str | None) -> None:
    assert parse_api_level(source) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  NGS LIBRARY PREP ", "NGS Library Prep"),
        ("Proteins & Proteiomics", "Proteins & Proteomics"),
        ("Nucleic Acid Purification & Extraction", "Nucleic Acid Extraction & Purification"),
        ("PCR prep", "PCR Prep"),
        ("qpcr  setup", "qPCR Setup"),
        ("Cherry Picking", "Cherrypicking"),
        ("plate filling", "Plate Filling"),
        ("Zymo RiboFree™ Total RNA Library Prep", "Zymo RiboFree™ Total RNA Library Prep"),
    ],
)
def test_normalise_category(raw: str, expected: str) -> None:
    assert normalise_category(raw) == expected


def test_categories_section_stops_at_prose_and_merges_duplicates() -> None:
    readme = (
        "# T\n\n## Categories\n* SAMPLE PREP\n- Sample Prep\n     * Plate Filling\n\n"
        "Explanation of parameters:\n* `mount`: which side\n\n## Description\n* not a category\n"
    )
    raw, top, sub = parse_categories(readme)
    assert raw == ["SAMPLE PREP", "Sample Prep", "Plate Filling"]
    assert top == ["Sample Prep"]
    assert sub == ["Plate Filling"]


def test_tip_reuse_parameters(make_folder: Callable[..., Path]) -> None:
    yes_no = [{"label": "No", "value": False}, {"label": "Yes", "value": True}]
    reuse = [
        {"type": "dropDown", "name": "park_tips", "label": "park tips", "options": yes_no},
        {"type": "dropDown", "name": "TIPREUSE", "label": "Reuse Tips?", "options": yes_no},
        {"type": "dropDown", "name": "PARK", "label": "Park tips?", "options": yes_no},
        {"type": "dropDown", "name": "tip_strategy", "label": "Tip Strategy", "options": yes_no},
        {"type": "dropDown", "name": "change_tips", "label": "change tips", "options": yes_no},
        {"type": "dropDown", "name": "same_tip", "label": "Use Same Tip?", "options": yes_no},
        {"type": "dropDown", "name": "is_reuse_reag_tips", "label": "Reuse?", "options": yes_no},
        {"type": "int", "name": "num_cycles", "label": "Cycles before new tip", "default": 20},
    ]
    other = [
        {"type": "dropDown", "name": "tip_track", "label": "track tips across protocol runs",
         "options": yes_no},
        {"type": "dropDown", "name": "track_tips", "label": "Track tips?", "options": yes_no},
        {"type": "dropDown", "name": "tiprack_name", "label": "Change tip rack", "options": yes_no},
        {"type": "int", "name": "start_tip", "label": "Starting tip (new box = 1)", "default": 1},
        {"type": "dropDown", "name": "touch_tip", "label": "Touch Tip?", "options": yes_no},
        {"type": "dropDown", "name": "filter_tip", "label": "Use Filter Tips?", "options": yes_no},
        {"type": "float", "name": "volume", "label": "Volume to change", "default": 5.0},
    ]  # fmt: skip
    [protocol] = discover(make_folder(fields=reuse + other))
    found = tip_reuse_parameters(protocol)
    assert [f.name for f in found] == [f["name"] for f in reuse]
    assert found[0].type == "dropDown" and found[0].default is False
    assert found[0].options == yes_no
    assert found[-1].default == 20 and found[-1].options == []


def test_no_fields_json_means_no_parameters(make_folder: Callable[..., Path]) -> None:
    [protocol] = discover(make_folder(fields=None))
    assert tip_reuse_parameters(protocol) == []


@pytest.mark.network
def test_fetch_is_pinned_idempotent_and_matches_the_survey(tmp_path: Path) -> None:
    checkout = fetch(tmp_path / "library")
    assert fetch(checkout) == checkout  # second call: already there
    head = (checkout / ".git" / "HEAD").read_text().strip()
    assert head == LIBRARY_COMMIT
    protocols = discover(checkout)
    assert len(protocols) == 833
    assert sum(1 for p in protocols if tip_reuse_parameters(p)) == 65
    assert json.loads((checkout / "protocols" / "00222e" / "fields.json").read_text())
    assert (checkout / "protolib" / "parse" / "parseOT2v2.py").is_file()
