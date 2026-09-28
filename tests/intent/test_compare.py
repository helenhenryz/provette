from __future__ import annotations

import pytest

from provette.intent.compare import compare, tolerance_ul
from provette.intent.spec import PlateMapError
from provette.state import replay
from tests.intent.helpers import free_map, pcr_map, pcr_trace


def _kinds(report):  # type: ignore[no-untyped-def]
    return sorted((r.well, i.kind, i.liquid) for r in report.wells for i in r.issues)


def test_a_correct_protocol_verifies() -> None:
    trace = pcr_trace()
    report = compare(trace, replay(trace), pcr_map())
    assert report.status == "verified"
    assert report.destination == "1:nest_96_wellplate_100ul_pcr_full_skirt"
    assert len(report.wells) == 4 and not report.mismatches


def test_a_wrong_volume_is_reported_with_both_numbers() -> None:
    trace = pcr_trace(sample_ul=8)
    report = compare(trace, replay(trace), pcr_map())
    assert report.status == "mismatch"
    issue = report.mismatches[0].issues[0]
    assert (issue.kind, issue.expected_ul, issue.found_ul) == ("wrong_amount", 5, 8)
    assert len(report.mismatches) == 4


def test_two_samples_swapped_are_seen_when_positions_are_pinned() -> None:
    trace = pcr_trace(sample_order=(1, 0, 2, 3))
    report = compare(trace, replay(trace), pcr_map())
    assert _kinds(report) == [
        ("A1", "missing_liquid", "sample_1"),
        ("A1", "unexpected_liquid", "sample_2"),
        ("B1", "missing_liquid", "sample_2"),
        ("B1", "unexpected_liquid", "sample_1"),
    ]


def test_a_position_free_map_cannot_see_a_swap_but_notes_the_order() -> None:
    trace = pcr_trace(sample_order=(1, 0, 2, 3))
    report = compare(trace, replay(trace), free_map())
    assert report.status == "verified"  # the limit of intent that does not pin positions
    assert any("not in the order" in note for note in report.notes)
    in_order = pcr_trace()
    assert not compare(in_order, replay(in_order), free_map()).notes


def test_a_position_free_map_accepts_any_wells() -> None:
    trace = pcr_trace(dests=("C5", "C6", "C7", "C8"))
    report = compare(trace, replay(trace), free_map())
    assert report.status == "verified"
    assert sorted(r.well for r in report.wells) == ["C5", "C6", "C7", "C8"]


def test_a_sample_that_never_arrives_is_a_missing_liquid_in_a_group() -> None:
    trace = pcr_trace(drop_sample_in_tip=2)
    report = compare(trace, replay(trace), free_map())
    assert _kinds(report) == [("C1", "missing_liquid", "sample_3")]


def test_an_extra_well_on_the_plate_is_reported() -> None:
    trace = pcr_trace(dests=("A1", "B1", "C1", "D1"))
    smaller = pcr_map()
    pinned = {w: c for w, c in smaller.variants[0].pinned.items() if w != "D1"}
    three = pcr_map(variants=[{"name": "three", "why": "", "pinned": pinned, "groups": []}])
    report = compare(trace, replay(trace), three)
    assert _kinds(report) == [("D1", "unexpected_well", None)]


def test_an_empty_pinned_well() -> None:
    trace = pcr_trace(dests=("A1", "B1", "C1", "E1"))
    report = compare(trace, replay(trace), pcr_map())
    assert ("D1", "well_empty", None) in _kinds(report)
    assert ("E1", "unexpected_well", None) in _kinds(report)


def test_a_liquid_that_binds_to_nothing_is_cannot_check_never_a_pass() -> None:
    trace = pcr_trace()
    wrong = pcr_map(
        liquids=[
            {"name": "master_mix", "role": "reagent", "bind": "name", "pattern": "SYBR"},
            {"name": "sample_{i}", "role": "sample", "bind": "indexed",
             "pattern": r"sample (\d+)", "count": 4},
        ]
    )  # fmt: skip
    report = compare(trace, replay(trace), wrong)
    assert report.status == "cannot_check"
    assert "master_mix" in report.problems[0]


def test_a_destination_regex_that_matches_nothing_is_cannot_check() -> None:
    trace = pcr_trace()
    report = compare(
        trace, replay(trace), pcr_map(destination={"select": "regex", "pattern": "ELISA"})
    )
    assert report.status == "cannot_check"


def test_any_variant_may_match() -> None:
    trace = pcr_trace(sample_ul=8)
    base = pcr_map().variants[0]
    eight = {w: {**c, f"sample_{i}": 8} for i, (w, c) in enumerate(base.pinned.items(), 1)}
    both = pcr_map(
        variants=[
            {"name": "five", "why": "", "pinned": {w: dict(c) for w, c in base.pinned.items()}},
            {"name": "eight", "why": "", "pinned": eight},
        ]
    )
    report = compare(trace, replay(trace), both)
    assert (report.status, report.variant) == ("verified", "eight")


def test_tolerance() -> None:
    assert tolerance_ul(100) == pytest.approx(2.0)
    assert tolerance_ul(2.38) >= 0.05  # 500/210 written as 2.4 must pass
    assert tolerance_ul(0.05) < 0.05  # the far end of a dilution series is not a free pass


def test_validation_names_the_problem() -> None:
    with pytest.raises(PlateMapError, match="not one of the map's liquids"):
        pcr_map(variants=[{"name": "x", "why": "", "pinned": {"A1": {"dye": 5}}}])
    with pytest.raises(PlateMapError, match="capture group"):
        pcr_map(liquids=[{"name": "s_{i}", "role": "sample", "bind": "indexed", "pattern": "s"}])
