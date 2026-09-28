"""`measure_export` counts what the replay export holds, on a hand-built export (no simulator)."""

from __future__ import annotations

from provette.corpus.workers import measure_export
from provette.view import export
from tests.view.test_export import hand_built


def test_measure_counts_the_hand_built_export() -> None:
    result = hand_built()
    data = export(result)
    measured = measure_export(data, (event.module for event in result.trace.events))
    assert measured["events"] == len(result.trace.events) == len(data["events"])
    assert measured["ops"]["aspirate"] == 9 and measured["ops"]["delay"] == 1
    assert measured["passed_on"] == 0
    assert [row["id"] for row in measured["labware"]] == [
        row["id"] for row in data["deck"]["labware"]
    ]
    assert measured["modules"] == ["temperatureModuleV2"]  # the builder's flat plate sits on one
    assert measured["event_modules"] == []  # and no event ever touched it
    assert measured["origins"] == 5 and measured["origins_declared"] == 5
    assert measured["orphan_wells"] == 0
    # the builder's tube rack is not the shipped one (its wells differ), so it is the one guess;
    # the builder gives no well a height table, so every well is drawn as a straight column
    by_id = {row["id"]: row for row in measured["labware"]}
    assert measured["unmatched"] == ["opentrons_24_tuberack_nest_1.5ml_snapcap"]
    assert not by_id["2:opentrons_24_tuberack_nest_1.5ml_snapcap"]["measured"]
    assert by_id["1:nest_96_wellplate_100ul_pcr_full_skirt"]["measured"]
    assert measured["wells_without_shape"] == sum(row["wells"] for row in measured["labware"])
    assert measured["bands"] > 0 and measured["bands_unknown_volume"] == 0


def test_measure_sees_a_module_only_the_events_name() -> None:
    data = export(hand_built())
    measured = measure_export(data, ["heaterShakerModuleV1", None, "heaterShakerModuleV1"])
    assert measured["event_modules"] == ["heaterShakerModuleV1"]
    assert "heaterShakerModuleV1" not in measured["modules"]  # nothing on the deck sits on it


def test_measure_flags_a_labware_off_the_deck_and_an_orphan_well() -> None:
    data = export(hand_built())
    data["deck"]["labware"][0]["slot"] = "offDeck"
    data["wells"].append("nowhere:1[A1]")
    measured = measure_export(data)
    assert measured["off_deck"] == [data["deck"]["labware"][0]["id"]]
    assert measured["orphan_wells"] == 1
