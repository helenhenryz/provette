"""The tracer against the fixture protocols. Every test here launches the simulator.

Line numbers below are lines of the files in tests/fixtures/protocols/: if you edit a fixture,
expect to edit its test.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from provette.model import Trace, WellKey
from provette.trace import TraceError, analyze_protocol, cross_check, trace_protocol
from tests.trace.conftest import GOOD, PROTOCOLS, analyzed, brief, liquid, traced

pytestmark = pytest.mark.sim

COLUMN = "A{0},B{0},C{0},D{0},E{0},F{0},G{0},H{0}"


# -- layer 2 of the validation loop ---------------------------------------------------------


@pytest.mark.parametrize("name", GOOD)
def test_broker_trace_and_analysis_agree(name: str) -> None:
    assert cross_check(traced(name), list(analyzed(name))) == []


def test_cross_check_notices_a_tampered_event() -> None:
    trace = traced("pcr_buggy")
    ops = list(analyzed("pcr_buggy"))
    victim = next(e for e in trace.events if e.op == "dispense")

    wrong_volume = dataclasses.replace(victim, volume_ul=(victim.volume_ul or 0) + 1)
    wrong_well = dataclasses.replace(
        victim,
        targets=[
            dataclasses.replace(t, well=WellKey(t.well.labware_id, "H12")) for t in victim.targets
        ],
    )
    for forged in (wrong_volume, wrong_well):
        events = [forged if e.index == victim.index else e for e in trace.events]
        problems = cross_check(Trace(trace.deck, events), ops)
        assert len(problems) == 1 and f"event {victim.index}" in problems[0]

    dropped = [e for e in trace.events if e.index != victim.index]
    assert cross_check(Trace(trace.deck, dropped), ops)  # everything after it is out of step


# -- the deck header's geometry ----------------------------------------------------------------


def test_deck_carries_the_wells_shape_from_the_labware_definition() -> None:
    """pcr_clean loads a NEST 1.5 ml tube rack, a NEST PCR plate and a 300 ul tip rack at
    API 2.19, where the simulator's own definitions carry no shape: it comes from the newest
    version of each (D-14), and the tips have none."""
    labware = {lw.load_name: lw for lw in traced("pcr_clean").deck.labware}
    tube = labware["opentrons_24_tuberack_nest_1.5ml_snapcap"].wells["A1"]
    pcr = labware["nest_96_wellplate_100ul_pcr_full_skirt"].wells["A1"]
    tips = labware["opentrons_96_tiprack_300ul"].wells["A1"]
    assert (tube.bottom_shape, pcr.bottom_shape, tips.bottom_shape) == ("v", "v", None)
    assert tips.height_at_ul is None and not tips.height_known
    for well in (tube, pcr):
        assert well.height_at_ul is not None and well.height_known
        assert well.height_at_ul[0] == (0.0, 0.0)
        volumes = [v for v, _ in well.height_at_ul]
        heights = [h for _, h in well.height_at_ul]
        assert volumes == sorted(volumes) and heights == sorted(heights)
    assert tube.height_at_ul is not None and tube.height_at_ul[-1][1] == tube.depth_mm
    # 20 uL in the tube's cone stands about 2.2 mm deep; as a column it would be 0.34 mm.
    from provette.state.contact import surface_mm

    assert 2.0 < (surface_mm(tube, 20) or 0) < 2.5
    assert 0.2 < (surface_mm(pcr, 2) or 0) < 1.0


# -- exact event sequences ------------------------------------------------------------------


def test_pcr_buggy_is_one_tip_through_every_tube() -> None:
    trace = traced("pcr_buggy")
    tubes = ["B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2"]
    expected: list[tuple[object, ...]] = [("pick_up_tip", 27, None, None, "A1", "A1")]
    for number, tube in enumerate(tubes, start=1):
        expected += [
            ("aspirate", 30, None, 20.0, tube, "A1"),
            ("dispense", 31, None, 20.0, f"A{number}", "A1"),
            ("aspirate", 32, None, 40.0, "A1", "A1"),
            ("dispense", 33, None, 40.0, f"A{number}", "A1"),
        ]
    expected.append(("drop_tip", 34, None, None, "A1", "A1"))
    assert [brief(e) for e in trace.events] == expected
    assert [e.index for e in trace.events] == list(range(34))
    assert {e.mount for e in trace.events} == {"right"}
    assert trace.events[1].targets[0].well == WellKey(
        "2:opentrons_24_tuberack_nest_1.5ml_snapcap", "B1"
    )
    assert trace.events[1].targets[0].tip == WellKey("3:opentrons_96_tiprack_300ul", "A1")
    assert trace.events[1].height_mm == 1.0  # the default: 1 mm above the bottom of the tube


def test_pcr_buggy_deck_and_liquids() -> None:
    deck = traced("pcr_buggy").deck
    assert (deck.protocol_name, deck.api_level, deck.opentrons_version) == (
        "pcr_buggy.py",
        "2.27",
        "8.8.2",
    )
    assert [lw.labware_id for lw in deck.labware] == [
        "1:nest_96_wellplate_100ul_pcr_full_skirt",
        "2:opentrons_24_tuberack_nest_1.5ml_snapcap",
        "3:opentrons_96_tiprack_300ul",
        "12:fixedTrash",
    ]
    plate, rack, tips, trash = deck.labware
    assert tips.is_tiprack and not plate.is_tiprack
    assert len(plate.wells) == 96 and len(rack.wells) == 24 and trash.wells == {}
    well = plate.wells["A1"]
    assert (well.shape, well.max_volume_ul, well.diameter_mm) == ("circular", 100, 5.34)
    assert well.depth_mm > 10
    [pipette] = deck.pipettes
    assert dataclasses.astuple(pipette) == ("right", "p300_single_gen2", 1, 20.0, 300.0)
    loads = deck.liquid_loads
    assert [(ld.well.well, ld.liquid_name, ld.volume_ul) for ld in loads[:2]] == [
        ("A1", "PCR master mix", 1000.0),
        ("B1", "sample 1", 100.0),
    ]
    assert loads[0].description == "2x master mix" and loads[0].line == 22
    assert len(loads) == 9 and {ld.line for ld in loads[1:]} == {25}


def test_helpers_and_loops_give_the_line_inside_the_helper_and_the_call_chain() -> None:
    events = traced("helpers_loops").events
    first_column = [
        ("pick_up_tip", 20, None, None, "A1", "A1"),
        ("aspirate", 14, None, 50.0, "A1", "A1"),
        ("dispense", 15, None, 50.0, "A1", "A1"),
        ("other", 16, None, None, "", ""),  # the MIX announcement
        ("aspirate", 16, "mix", 50.0, "A1", "A1"),
        ("dispense", 16, "mix", 50.0, "A1", "A1"),
        ("aspirate", 16, "mix", 50.0, "A1", "A1"),
        ("dispense", 16, "mix", 50.0, "A1", "A1"),
        ("drop_tip", 22, None, None, "A1", "A1"),
    ]
    assert [brief(e) for e in events[:9]] == first_column
    assert brief(events[9]) == ("pick_up_tip", 20, None, None, "B1", "B1")
    assert brief(events[11]) == ("dispense", 15, None, 50.0, "A2", "B1")
    assert events[0].stack == ["run:32", "with_fresh_tip:20"]
    assert events[1].stack == ["run:32", "with_fresh_tip:21", "add_and_mix:14"]
    assert events[3].raw_op == "command.MIX" and events[3].detail.startswith("Mixing 2 times")


def test_transfer_family_parents_air_gaps_and_blow_out() -> None:
    events = traced("transfer_family").events
    assert [brief(e) for e in events[:6]] == [
        ("other", 25, None, None, "", ""),
        ("pick_up_tip", 25, "transfer", None, "A1", "A1"),
        ("aspirate", 25, "transfer", 50.0, "A1", "A1"),
        ("other", 25, "transfer", None, "", ""),  # the AIR_GAP announcement
        ("aspirate", 25, "air_gap", 20.0, "A1", "A1"),  # the air itself
        ("dispense", 25, "transfer", 70.0, "A1", "A1"),  # 50 of liquid and 20 of air
    ]
    gap = events[4]
    assert gap.raw_op == "command.AIR_GAP"
    assert gap.height_mm == pytest.approx(37.9 + 5)  # 5 mm above the top of a 37.9 mm tube
    assert gap.targets[0].well.labware_id == "2:opentrons_24_tuberack_nest_1.5ml_snapcap"
    assert [e.parent for e in events[6:13]] == ["transfer"] + ["mix"] * 6
    assert events[14].targets[0].tip == WellKey("3:opentrons_96_tiprack_300ul", "B1")

    # distribute() and consolidate() are built on transfer(): the parent is what the author wrote
    distribute = [e for e in events if e.line == 30]
    assert [e.raw_op for e in distribute[:2]] == ["command.DISTRIBUTE", "command.TRANSFER"]
    assert [brief(e) for e in distribute[2:]] == [
        ("pick_up_tip", 30, "distribute", None, "C1", "C1"),
        ("aspirate", 30, "distribute", 110.0, "A1", "C1"),  # 3 x 30 and a 20 uL disposal volume
        ("dispense", 30, "distribute", 30.0, "B1", "C1"),
        ("dispense", 30, "distribute", 30.0, "B2", "C1"),
        ("dispense", 30, "distribute", 30.0, "B3", "C1"),
        ("blow_out", 30, "distribute", None, "A1", "C1"),  # back into the source tube
        ("drop_tip", 30, "distribute", None, "A1", "C1"),
    ]
    blow_out = distribute[-2]
    assert blow_out.targets[0].well.labware_id.startswith("2:")
    assert blow_out.height_mm == pytest.approx(37.9)  # at the top of the tube
    consolidate = [brief(e) for e in events if e.line == 35 and e.op != "other"]
    assert consolidate == [
        ("pick_up_tip", 35, "consolidate", None, "D1", "D1"),
        ("aspirate", 35, "consolidate", 40.0, "B1", "D1"),
        ("aspirate", 35, "air_gap", 10.0, "B1", "D1"),
        ("aspirate", 35, "consolidate", 40.0, "B2", "D1"),
        ("aspirate", 35, "air_gap", 10.0, "B2", "D1"),
        ("dispense", 35, "consolidate", 100.0, "A2", "D1"),
        ("drop_tip", 35, "consolidate", None, "A1", "D1"),
    ]


def test_estimated_time_never_goes_back_and_counts_delays() -> None:
    events = traced("pcr_clean").events
    times = [e.t_est_s for e in events]
    assert times == sorted(times) and times[0] == 0.0
    delay = next(e for e in events if e.op == "delay")
    after = events[delay.index + 1]
    assert delay.duration_s == 300.0
    assert after.t_est_s - delay.t_est_s == pytest.approx(300.0)


# -- multi-channel (DECISIONS.md D-11) ------------------------------------------------------


def test_multi_channel_is_expanded_to_the_wells_every_tip_enters() -> None:
    trace = traced("multi_channel")
    tips1, tips2 = COLUMN.format(1), COLUMN.format(2)
    assert [brief(e) for e in liquid(trace)] == [
        ("pick_up_tip", 26, None, None, tips1, tips1),
        ("aspirate", 27, None, 100.0, ",".join(["A1"] * 8), tips1),  # a reservoir: one trough
        ("dispense", 28, None, 100.0, COLUMN.format(1), tips1),
        ("drop_tip", 29, None, None, ",".join(["A1"] * 8), tips1),
        ("pick_up_tip", 32, None, None, tips2, tips2),
        ("aspirate", 33, None, 40.0, ",".join(["A1"] * 8), tips2),
        ("dispense", 34, None, 20.0, "A1,C1,E1,G1,I1,K1,M1,O1", tips2),  # 384 wells
        ("dispense", 35, None, 20.0, "B1,D1,F1,H1,J1,L1,N1,P1", tips2),
        ("drop_tip", 36, None, None, tips2, tips2),
    ]
    returned = trace.events[-1]
    assert returned.returned and trace.events[-2].raw_op == "command.RETURN_TIP"
    assert not trace.events[3].returned
    assert {e.mount for e in trace.events} == {"left"}
    assert trace.deck.pipettes[0].channels == 8
    assert trace.deck.labware[0].label == "assay plate"
    reservoir = trace.deck.labware[1].wells["A1"]
    assert reservoir.shape == "rectangular" and reservoir.diameter_mm is None
    assert reservoir.x_mm and reservoir.y_mm and reservoir.y_mm > 8 * 9 - 9


def test_partial_pickup_lists_only_the_tips_that_are_there() -> None:
    events = traced("partial_tips").events
    single_nozzle = [brief(e) for e in events if e.line in (28, 29, 30, 31)]
    assert single_nozzle == [
        ("pick_up_tip", 28, None, None, "C1", "C1"),
        ("aspirate", 29, None, 30.0, "A2", "C1"),
        ("dispense", 30, None, 30.0, "C1", "C1"),
        ("drop_tip", 31, None, None, "A1", "C1"),
    ]
    six = "B1,D1,E1,F1,G1,H1"  # A1 was thrown away, C1 was thrown away, B1 was put back
    partly_empty_column = [brief(e) for e in events if (e.line or 0) >= 36 and e.op != "other"]
    assert partly_empty_column == [
        ("pick_up_tip", 36, None, None, six, six),
        ("aspirate", 37, None, 30.0, ",".join(["A3"] * 6), six),
        ("dispense", 38, None, 30.0, "B5,D5,E5,F5,G5,H5", six),
        ("drop_tip", 39, None, None, six, six),
    ]
    put_back = next(e for e in events if e.line == 24 and e.op == "drop_tip")
    assert put_back.returned and put_back.parent == "transfer"


# -- modules --------------------------------------------------------------------------------


def test_module_events() -> None:
    trace = traced("modules")
    cold = "6:nest_96_wellplate_100ul_pcr_full_skirt"
    pcr = "7:nest_96_wellplate_100ul_pcr_full_skirt"
    shaken = "1:opentrons_96_flat_bottom_adapter_nest_wellplate_200ul_flat"
    tm, tc, hs = "temperatureModuleV2", "thermocyclerModuleV2", "heaterShakerModuleV1"
    environment = [
        (e.op, e.line, e.module, e.labware_id, e.celsius, e.duration_s)
        for e in trace.events
        if e.mount is None and e.op != "other"
    ]
    assert environment == [
        ("set_temperature", 23, tm, cold, 4.0, None),
        ("lid", 24, tc, pcr, None, None),
        ("lid", 25, hs, shaken, None, None),
        ("set_temperature", 33, hs, shaken, 37.0, None),
        ("delay", 35, None, None, None, 30.0),
        ("deactivate", 37, hs, shaken, None, None),
        ("lid", 38, hs, shaken, None, None),
        ("lid", 40, tc, pcr, None, None),
        ("set_temperature", 42, tc, pcr, 95.0, None),
        ("thermocycler_profile", 43, tc, pcr, None, None),
        ("set_temperature", 51, tc, pcr, 4.0, None),
        ("lid", 52, tc, pcr, None, None),
        ("pause", 53, None, None, None, None),
        ("delay", 54, None, None, None, 60.0),
        ("deactivate", 55, tc, pcr, None, None),
        ("deactivate", 56, tm, cold, None, None),
    ]
    lids = [e.detail.split(":")[0] for e in trace.events if e.op == "lid"]
    assert lids == ["open", "close", "open", "close", "open"]
    others = [e.raw_op.removeprefix("command.") for e in trace.events if e.op == "other"]
    assert others == [
        "HEATER_SHAKER_WAIT_FOR_TEMPERATURE",
        "HEATER_SHAKER_SET_AND_WAIT_FOR_SHAKE_SPEED",
        "HEATER_SHAKER_DEACTIVATE_SHAKER",
        "THERMOCYCLER_SET_LID_TEMP",
    ]
    profile = next(e for e in trace.events if e.op == "thermocycler_profile")
    assert "3 repetitions" in profile.detail and "'temperature': 60" in profile.detail
    pause = next(e for e in trace.events if e.op == "pause")
    assert "Take the plate out" in pause.detail

    on_modules = {lw.labware_id: (lw.module, lw.slot, lw.label) for lw in trace.deck.labware}
    assert on_modules[cold] == (tm, "6", "reagents on ice")
    assert on_modules[pcr] == (tc, "7", None)
    assert on_modules[shaken] == (hs, "1", None)
    assert on_modules["9:opentrons_96_tiprack_300ul"] == (None, "9", None)
    wells = [str(e.targets[0].well) for e in trace.events if e.op in ("aspirate", "dispense")]
    assert wells == [f"{cold}[A1]", f"{pcr}[A1]", f"{shaken}[A1]"]
    assert all(e.height_mm == 1.0 for e in trace.events if e.op in ("aspirate", "dispense"))


# -- the old engine (API below 2.14) ---------------------------------------------------------


def test_old_api_level_traces_the_same_way() -> None:
    trace = traced("legacy_api")
    assert trace.deck.api_level == "2.11"
    trash = ",".join(["A1"] * 8)
    assert [brief(e) for e in liquid(trace)] == [
        ("set_temperature", 21, None, None, "", ""),
        ("pick_up_tip", 24, None, None, "A1", "A1"),
        ("aspirate", 25, None, 50.0, "A1", "A1"),
        ("aspirate", 26, "air_gap", 10.0, "A1", "A1"),
        ("dispense", 27, None, 60.0, "A1", "A1"),
        ("blow_out", 28, None, None, "A1", "A1"),
        ("touch_tip", 29, None, None, "A1", "A1"),
        ("drop_tip", 30, None, None, "A1", "A1"),
        ("pick_up_tip", 33, "transfer", None, "B1", "B1"),
        ("aspirate", 33, "transfer", 30.0, "A2", "B1"),
        ("dispense", 33, "transfer", 30.0, "A2", "B1"),
        ("aspirate", 33, "mix", 20.0, "A2", "B1"),
        ("dispense", 33, "mix", 20.0, "A2", "B1"),
        ("aspirate", 33, "mix", 20.0, "A2", "B1"),
        ("dispense", 33, "mix", 20.0, "A2", "B1"),
        ("drop_tip", 33, "transfer", None, "A1", "B1"),
        ("pick_up_tip", 36, None, None, COLUMN.format(1), COLUMN.format(1)),
        ("aspirate", 37, None, 100.0, trash, COLUMN.format(1)),
        ("dispense", 38, None, 100.0, COLUMN.format(3), COLUMN.format(1)),
        ("drop_tip", 39, None, None, trash, COLUMN.format(1)),
        ("delay", 41, None, None, "", ""),
        ("deactivate", 42, None, None, "", ""),
    ]
    by_line = {e.line: e for e in liquid(trace)}
    depth = trace.deck.labware[0].wells["A1"].depth_mm
    assert by_line[25].height_mm == 1.0
    assert by_line[27].height_mm == pytest.approx(depth)  # dispense from the top of the well
    assert by_line[29].height_mm == pytest.approx(depth - 1)  # touch tip: 1 mm below the top
    cold_depth = trace.deck.labware[3].wells["A1"].depth_mm
    assert by_line[26].height_mm == pytest.approx(cold_depth + 5)  # the air gap, 5 mm above
    assert by_line[30].returned and by_line[30].mount == "right"
    assert by_line[21].celsius == 4.0 and by_line[21].module == "temperatureModuleV2"
    assert by_line[21].labware_id == "4:nest_96_wellplate_100ul_pcr_full_skirt"
    # Below 2.14 the trash is an ordinary labware with one well
    assert str(by_line[39].targets[0].well) == "12:opentrons_1_trash_1100ml_fixed[A1]"
    assert trace.deck.labware[-1].load_name == "opentrons_1_trash_1100ml_fixed"
    assert trace.deck.labware[0].label == "assay plate"
    assert [p.mount for p in trace.deck.pipettes] == ["left", "right"]


# -- move_labware and the ways to declare a liquid -------------------------------------------


def test_a_moved_plate_keeps_its_id_and_liquid_loads_are_recorded() -> None:
    trace = traced("move_labware")
    plate = "1:nest_96_wellplate_200ul_flat"
    move = next(e for e in trace.events if e.op == "move_labware")
    assert (move.line, move.labware_id) == (25, plate) and "slot 5" in move.detail
    after = [e for e in trace.events if e.index > move.index and e.op in ("aspirate", "dispense")]
    assert [str(e.targets[0].well) for e in after] == [f"{plate}[C1]", f"{plate}[A1]"]
    assert [lw.labware_id for lw in trace.deck.labware][0] == plate
    loads = [
        (ld.well.well, ld.liquid_name, ld.volume_ul, ld.line) for ld in trace.deck.liquid_loads
    ]
    assert loads == [
        ("A1", "water", 8000.0, 16),  # Well.load_liquid
        ("A1", "water", 20.0, 17),  # Labware.load_liquid
        ("A2", "water", 20.0, 17),
        ("B1", "water", 10.0, 18),  # Labware.load_liquid_by_well
        ("B2", "water", 15.0, 18),
        ("C1", "", 0.0, 19),  # Labware.load_empty: declared empty, no liquid name
    ]
    assert trace.deck.liquid_loads[0].well.labware_id == "2:nest_12_reservoir_15ml"


# -- failure and determinism ------------------------------------------------------------------


def test_a_protocol_the_simulator_rejects_raises_trace_error() -> None:
    with pytest.raises(TraceError) as caught:
        trace_protocol(PROTOCOLS / "bad_protocol.py")
    assert caught.value.line == 15
    assert "Cannot aspirate 500" in str(caught.value)


def test_a_protocol_that_never_ends_raises_trace_error() -> None:
    with pytest.raises(TraceError, match="did not finish within 5 s"):
        trace_protocol(PROTOCOLS / "never_ends.py", timeout_s=5)


def test_a_missing_file_raises_trace_error(tmp_path: Path) -> None:
    with pytest.raises(TraceError, match="no such protocol"):
        trace_protocol(tmp_path / "nothing.py")


def test_tracing_twice_gives_the_same_trace(tmp_path: Path) -> None:
    first = traced("transfer_family")
    second = trace_protocol(PROTOCOLS / "transfer_family.py")
    assert first == second
    first.dump(tmp_path / "a.jsonl")
    assert Trace.load(tmp_path / "a.jsonl") == first


def test_trash_in_place_steps_and_a_plate_on_an_adapter() -> None:
    trace = traced("trash_and_adapter")
    assert [brief(e) for e in liquid(trace)][1:] == [
        ("pick_up_tip", 21, None, None, "A1", "A1"),
        ("aspirate", 22, None, 100.0, "A1", "A1"),
        ("dispense", 23, None, 50.0, "A1", "A1"),
        ("touch_tip", 24, None, None, "A1", "A1"),
        ("dispense", 25, None, 50.0, "A1", "A1"),
        ("blow_out", 26, None, None, "A1", "A1"),
        ("aspirate", 27, None, 30.0, "A1", "A1"),
        ("aspirate", 28, "air_gap", 20.0, "A1", "A1"),
        ("dispense", 29, None, 50.0, "A2", "A1"),
        ("blow_out", 30, None, None, "A2", "A1"),
        ("drop_tip", 31, None, None, "A1", "A1"),
    ]
    by_line = {e.line: e for e in liquid(trace)}
    plate, trash = "1:nest_96_wellplate_200ul_flat", "12:fixedTrash"
    where = {line: e.targets[0].well.labware_id for line, e in by_line.items() if e.targets}
    assert where[24] == plate and where[25] == trash and where[26] == trash
    assert where[28] == "5:nest_12_reservoir_15ml" and where[30] == plate
    assert by_line[25].height_mm is None  # no well, no height
    assert by_line[28].height_mm == 1.0  # in place: where the aspirate before it was
    assert by_line[30].height_mm == by_line[29].height_mm == pytest.approx(10.8)
    on_shaker = {lw.labware_id: lw.module for lw in trace.deck.labware if lw.slot == "1"}
    assert on_shaker == {
        plate: "heaterShakerModuleV1",
        "1:opentrons_96_flat_bottom_adapter": "heaterShakerModuleV1",
    }


# -- patterns found by cross-checking the public library ---------------------------------------


def test_a_refilled_rack_gives_tips_again() -> None:
    # 103 library protocols lost every target after their first refill before this was handled.
    events = liquid(traced("refilled_racks"))
    pickups = [brief(e) for e in events if e.op == "pick_up_tip"]
    assert pickups == [
        ("pick_up_tip", 18, "transfer", None, "A1", "A1"),
        ("pick_up_tip", 22, "transfer", None, "A1", "A1"),  # after reset_tipracks()
        ("pick_up_tip", 26, None, None, "A1", "A1"),  # after a pause, with no reset
    ]
    assert all(e.targets and e.targets[0].tip for e in events if e.mount)
    assert [e.targets[0].well.well for e in events if e.op == "dispense"] == ["A1", "A2", "A3"]


def test_zero_volume_too_much_volume_and_steps_with_no_place_named() -> None:
    trace = traced("odd_volumes")
    assert [brief(e) for e in liquid(trace)] == [
        ("pick_up_tip", 15, None, None, "A1", "A1"),
        ("dispense", 18, None, 0.0, "A1", "A1"),  # the tip enters the well and moves nothing
        ("aspirate", 21, None, 90.0, "A1", "A1"),
        ("dispense", 22, None, 90.0, "A1", "A1"),  # asked for 200, held 90
        ("aspirate", 26, None, 30.0, "A2", "A1"),  # no place named: where move_to left the tip
        ("dispense", 27, None, 30.0, "A2", "A1"),
        ("aspirate", 28, "mix", 20.0, "A2", "A1"),
        ("dispense", 28, "mix", 20.0, "A2", "A1"),
        ("aspirate", 28, "mix", 20.0, "A2", "A1"),
        ("dispense", 28, "mix", 20.0, "A2", "A1"),
        ("blow_out", 29, None, None, "A2", "A1"),
        ("dispense", 30, None, 0.0, "A3", "A1"),  # asked for 60 with an empty tip
        ("drop_tip", 31, None, None, "A1", "A1"),
    ]
    assert "200.0 uL" in trace.events[3].detail  # the simulator's text keeps what was asked
    unnamed = [e for e in liquid(trace) if e.line in (26, 27, 28, 29)]
    assert {e.height_mm for e in unnamed} == {2.0}
    assert {e.targets[0].well.labware_id for e in unnamed} == {"1:nest_96_wellplate_200ul_flat"}


def test_odd_volumes_on_the_new_engine(tmp_path: Path) -> None:
    # From API 2.14 the analysis is independent of the broker, and it agrees: 90, not 200.
    source = (PROTOCOLS / "odd_volumes.py").read_text(encoding="utf-8")
    copy = tmp_path / "odd_volumes.py"
    copy.write_text(source.replace('"apiLevel": "2.13"', '"apiLevel": "2.15"'), encoding="utf-8")
    trace = trace_protocol(copy)
    ops = analyze_protocol(copy)
    assert trace.deck.api_level == "2.15"
    assert cross_check(trace, ops) == []
    assert [o.volume_ul for o in ops if o.op == "dispense"][:2] == [0.0, 90.0]
    assert [o.volume_ul for o in ops if o.op == "dispense"][-1] == 0.0  # 60 asked, tip empty


def test_every_tip_has_a_target_even_over_no_well() -> None:
    # Found by the state machine on library traces: an aspirate listing 4 tips and the matching
    # dispense 8 looks like liquid from nowhere.
    events = liquid(traced("multi_tube_rack"))
    tips = COLUMN.format(1)
    assert [brief(e) for e in events] == [
        ("pick_up_tip", 19, None, None, tips, tips),
        ("aspirate", 20, None, 40.0, "A1,A1,B1,A1,C1,A1,D1,A1", tips),  # even tips: the named tube
        ("dispense", 21, None, 40.0, tips, tips),
        ("drop_tip", 22, None, None, tips, tips),
    ]


@pytest.mark.parametrize("name", GOOD)
def test_the_tips_on_a_pipette_do_not_change_between_pick_up_and_drop(name: str) -> None:
    on: dict[str | None, list[WellKey | None]] = {}
    for event in traced(name).events:
        tips = [t.tip for t in event.targets]
        if event.op == "pick_up_tip":
            on[event.mount] = tips
        elif event.op in ("aspirate", "dispense", "blow_out", "touch_tip", "drop_tip"):
            assert tips == on[event.mount], f"event {event.index}"
