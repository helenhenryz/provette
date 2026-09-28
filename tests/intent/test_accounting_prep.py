from __future__ import annotations

import pytest

from provette.intent.cli import verify_trace
from provette.intent.prep import needed_volumes
from provette.intent.report import report_json, report_text
from provette.state import replay
from tests.intent.helpers import pcr_map, pcr_trace
from tests.state.builder import tube


def test_everything_is_accounted_for_in_a_correct_run() -> None:
    trace = pcr_trace()
    result = verify_trace(trace, replay(trace), pcr_map())
    assert result.exit_code == 0
    mix = next(a for a in result.accounting.liquids if a.logical == "master_mix")
    assert (mix.declared_ul, mix.delivered_ul, mix.left_in_source_ul, mix.lost_ul) == (
        200,
        80,
        120,
        0,
    )
    for liquid in result.accounting.liquids:
        total = liquid.delivered_ul + liquid.left_in_source_ul + liquid.lost_ul
        assert total + sum(v for _, v in liquid.elsewhere) == pytest.approx(liquid.declared_ul)


def test_a_sample_thrown_away_inside_its_tip_is_flagged() -> None:
    trace = pcr_trace(drop_sample_in_tip=1)
    result = verify_trace(trace, replay(trace), pcr_map())
    flagged = result.accounting.flagged
    assert [a.logical for a in flagged] == ["sample_2"]
    assert flagged[0].lost_ul == pytest.approx(5)
    assert "inside a tip" in flagged[0].flags[0]
    assert result.exit_code == 1


def test_a_spare_volume_smaller_than_one_dose_is_a_note_not_a_flag() -> None:
    trace = pcr_trace(spare_ul=1)
    result = verify_trace(trace, replay(trace), pcr_map())
    assert not result.accounting.flagged and result.exit_code == 0
    sample = next(a for a in result.accounting.liquids if a.logical == "sample_1")
    assert sample.lost_ul == pytest.approx(1) and "less than one well" in sample.notes[0]


def test_a_sample_put_in_a_well_the_map_does_not_list_is_flagged() -> None:
    trace = pcr_trace(trash_sample=3)
    result = verify_trace(trace, replay(trace), pcr_map())
    flagged = result.accounting.flagged
    assert [a.logical for a in flagged] == ["sample_4"]
    assert flagged[0].elsewhere[0][0] == tube("D6")


def test_discarding_is_not_flagged_when_the_map_says_it_is_intended() -> None:
    trace = pcr_trace(drop_sample_in_tip=1)
    result = verify_trace(trace, replay(trace), pcr_map(discard_intended=["sample_2"]))
    assert not result.accounting.flagged


def test_needed_volume_and_run_dry() -> None:
    trace = pcr_trace(mix_declared=60)
    run = replay(trace)
    assert needed_volumes(trace, run)[tube("A1")] == pytest.approx(80)
    result = verify_trace(trace, run, pcr_map())
    assert [(p.well, p.flag) for p in result.prep.flagged] == [(tube("A1"), "would_run_dry")]
    assert "WOULD RUN DRY" in report_text(result)


def test_no_margin() -> None:
    trace = pcr_trace(mix_declared=85)
    result = verify_trace(trace, replay(trace), pcr_map())
    assert [p.flag for p in result.prep.flagged] == ["no_margin"]
    assert result.intent.status == "verified" and result.exit_code == 1


def test_a_declared_well_only_dispensed_into_is_said_in_its_own_words() -> None:
    trace = pcr_trace(buffer_in_plate_ul=10)
    result = verify_trace(trace, replay(trace), pcr_map())
    line = next(p for p in result.prep.lines if p.liquid == "buffer")
    assert (line.declared_ul, line.needed_ul, line.flag) == (10, 0, None)
    assert line.already_in_plate and not result.prep.flagged
    text = report_text(result)
    assert "already in the plate: 10 ul declared, nothing drawn" in text
    assert "put in what is declared" in text
    row = next(p for p in report_json(result)["prep"]["lines"] if p["liquid"] == "buffer")
    assert row["already_in_plate"] and row["needed_ul"] == 0 and row["declared_ul"] == 10
    # the numbers of every other line are unchanged, and none of them is "already in the plate"
    assert not any(p.already_in_plate for p in result.prep.lines if p.liquid != "buffer")


def test_tips_are_counted_per_rack_and_the_json_is_complete() -> None:
    trace = pcr_trace()
    result = verify_trace(trace, replay(trace), pcr_map())
    assert [(t.slot, t.tips) for t in result.prep.tips] == [("3", 5)]
    row = report_json(result)
    assert row["intent"]["status"] == "verified" and row["exit_code"] == 0
    assert len(row["prep"]["lines"]) == 5
