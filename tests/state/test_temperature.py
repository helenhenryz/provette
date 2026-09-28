"""The clock and the temperature timeline."""

from __future__ import annotations

import pytest

from provette.state import TempInterval, replay, seconds_at_or_above
from tests.state.builder import ABOVE, FLAT_ID, RACK_ID, TraceBuilder, flat, tip, tube


def test_setpoints_become_intervals_per_labware() -> None:
    b = TraceBuilder()
    b.delay(60)  # 0..60 ambient
    b.set_temperature(FLAT_ID, 4)  # at 60, takes 1 s
    b.delay(600)  # 61..661
    b.set_temperature(FLAT_ID, 37)  # at 661
    b.delay(300)  # 662..962
    b.deactivate(FLAT_ID)  # at 962
    b.delay(100)  # 963..1063
    run = replay(b.trace())
    assert run.end_s == 1063
    assert run.labware_temperature(FLAT_ID, 0, run.end_s) == [
        TempInterval(0, 60, None),
        TempInterval(60, 661, 4),
        TempInterval(661, 962, 37),
        TempInterval(962, 1063, None),
    ]
    # A window inside one setpoint, and one that straddles two.
    assert run.labware_temperature(FLAT_ID, 100, 200) == [TempInterval(100, 200, 4)]
    assert run.labware_temperature(FLAT_ID, 600, 700) == [
        TempInterval(600, 661, 4),
        TempInterval(661, 700, 37),
    ]
    # Labware on no module is ambient throughout.
    assert run.labware_temperature(RACK_ID, 0, run.end_s) == [TempInterval(0, 1063, None)]
    assert run.labware_temperature(FLAT_ID, 50, 50) == []


def test_how_long_an_enzymes_material_was_warm_before_an_event() -> None:
    enzyme, reaction = flat("A1"), tube("A1")  # the enzyme sits on the temperature module
    b = TraceBuilder({enzyme: ("T4 ligase", 100.0)})
    t = tip("A1")
    b.set_temperature(FLAT_ID, 4)  # t=0
    b.delay(1000)  # cold: 1..1001
    b.deactivate(FLAT_ID)  # t=1001: the block is switched off with the enzyme still on it
    b.delay(500)  # 1002..1502
    b.pick_up(t)  # 1502
    b.aspirate(t, enzyme, 10)  # 1503
    moved = b.dispense(t, reaction, 10, height=ABOVE)  # 1504
    b.delay(200)  # 1505..1705
    end = b.delay(0)
    run = replay(b.trace())

    assert run.time_of(moved) == 1504
    path = run.material_temperature(enzyme, reaction, before_event=end)
    assert path == [
        TempInterval(0, 1001, 4),  # in its own well, cold
        TempInterval(1001, 1504, None),  # in its own well, block off
        TempInterval(1504, 1705, None),  # in the reaction tube, on the open deck
    ]
    assert seconds_at_or_above(path, celsius=20, ambient_celsius=22) == pytest.approx(704)
    assert seconds_at_or_above(path, celsius=20, ambient_celsius=18) == 0
    # The enzyme left in the stock well, asked about at the same moment.
    stock = run.material_temperature(enzyme, enzyme, before_event=end)
    assert seconds_at_or_above(stock, celsius=20, ambient_celsius=22) == pytest.approx(704)
    # Before it arrived, there is no material to ask about.
    assert run.material_temperature(enzyme, reaction, before_event=moved) == []
    assert run.material_temperature(enzyme, reaction, before_event=moved + 1) != []


def test_material_is_followed_through_an_intermediate_well() -> None:
    enzyme, premix, final = tube("A1"), flat("A1"), tube("B1")
    b = TraceBuilder({enzyme: ("enzyme", 100.0)})
    t = tip("A1")
    b.set_temperature(FLAT_ID, 37)  # t=0
    b.pick_up(t)  # 1
    b.aspirate(t, enzyme, 50)  # 2
    b.dispense(t, premix, 50, height=ABOVE)  # 3: onto the warm block
    b.delay(900)  # 4..904
    b.aspirate(t, premix, 20)  # 904
    b.dispense(t, final, 20, height=ABOVE)  # 905
    end = b.delay(60)  # 906..966
    run = replay(b.trace())
    path = run.material_temperature(enzyme, final, before_event=end + 1)
    assert path == [
        TempInterval(0, 3, None),
        TempInterval(3, 905, 37),
        TempInterval(905, 966, None),
    ]
    assert seconds_at_or_above(path, celsius=30, ambient_celsius=22) == 902
