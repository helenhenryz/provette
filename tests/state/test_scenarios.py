"""Hand-built protocols with the exact arrivals each must produce."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from provette.model import Trace, WellGeometry, WellKey
from provette.state import Arrival, Run, replay
from provette.state.contact import surface_mm
from tests.state.builder import (
    ABOVE,
    FLAT,
    FLAT_ID,
    LOW,
    RACK_ID,
    ROWS,
    TUBE,
    TraceBuilder,
    flat,
    plate,
    tip,
    trough,
    tube,
)

MM = tube("A1")
SAMPLES = [tube(name) for name in ["B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2"]]
PCR_LOADS = {MM: ("PCR master mix", 1000.0)} | {
    well: (f"sample {i + 1}", 100.0) for i, well in enumerate(SAMPLES)
}


def carryover(run: Run) -> list[Arrival]:
    return [arrival for arrival in run.arrivals if arrival.mode == "carryover"]


def where(arrivals: list[Arrival], well: WellKey) -> dict[WellKey, int]:
    """atom -> event index, for the arrivals into `well`."""
    return {arrival.atom: arrival.event_index for arrival in arrivals if arrival.well == well}


# ---------------------------------------------------------------------------------------------
# The two reference protocols (spikes/sim/pcr_buggy.py and pcr_clean.py), by hand
# ---------------------------------------------------------------------------------------------


def test_buggy_pcr_one_tip_contaminates_master_mix_plate_and_sample_tubes() -> None:
    b = TraceBuilder(PCR_LOADS)
    t = tip("A1")
    b.pick_up(t)  # event 0
    for i, sample in enumerate(SAMPLES):  # sample i uses events 4i+1 .. 4i+4
        b.aspirate(t, sample, 10)
        b.dispense(t, plate(f"A{i + 1}"), 10)
        b.aspirate(t, MM, 40)
        b.dispense(t, plate(f"A{i + 1}"), 40)
    b.drop(t)
    run = replay(b.trace())
    assert run.anomalies == ()

    # The master mix tube receives sample i when the tip that carried sample i enters it.
    dirty = carryover(run)
    assert where(dirty, MM) == {sample: 4 * i + 3 for i, sample in enumerate(SAMPLES)}
    assert all(a.certain and a.via_tip == t for a in dirty)
    assert run.wells[MM].atoms[SAMPLES[0]].mode == "carryover"
    assert run.wells[MM].volume_ul == pytest.approx(1000 - 8 * 40)

    # Sample tube j receives the master mix and every earlier sample when the dirty tip enters.
    assert where(dirty, SAMPLES[0]) == {}
    for j in range(1, 8):
        expected = dict.fromkeys([MM, *SAMPLES[:j]], 4 * j + 1)
        assert where(dirty, SAMPLES[j]) == expected

    # Plate well j holds its own sample, the master mix and every earlier sample.
    for j in range(8):
        atoms = run.wells[plate(f"A{j + 1}")].atoms
        assert set(atoms) == {MM, *SAMPLES[: j + 1]}
        assert atoms[SAMPLES[j]].volume_ul == pytest.approx(10)
        assert atoms[MM].volume_ul == pytest.approx(40)

    # downstream() says where sample 1 went, and what carried it to the master mix.
    reached = {a.well: a for a in run.downstream(SAMPLES[0])}
    assert set(reached) == {MM, *SAMPLES[1:], *(plate(f"A{j}") for j in range(1, 9))}
    assert reached[MM].source_well == SAMPLES[0]
    assert reached[plate("A1")].mode == "bulk"
    assert reached[plate("A1")].volume_ul == pytest.approx(10)
    # Sample 1 reaches plate A3 inside the liquid drawn from the dirtied tube: a trace, in bulk.
    assert (reached[plate("A3")].mode, reached[plate("A3")].volume_ul) == ("bulk", 0.0)


def test_buggy_pcr_contact_verdicts() -> None:
    b = TraceBuilder(PCR_LOADS)
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, SAMPLES[0], 10)
    b.dispense(t, plate("A1"), 10)  # 10 uL in a 5.34 mm well is 0.45 mm deep: tip at 1 mm is dry
    b.aspirate(t, MM, 40)
    b.dispense(t, plate("A1"), 40)  # 50 uL is 2.2 mm deep: the surface rose past the tip
    run = replay(b.trace())
    got = [(s.contacts[0].verdict, s.contacts[0].reason) for s in run.steps[1:]]
    assert got == [
        ("contact", "tip_below_surface"),
        ("no_contact", "tip_above_surface"),
        ("contact", "tip_below_surface"),
        ("contact", "tip_below_surface"),
    ]
    assert run.steps[4].contacts[0].surface_mm == pytest.approx(2.2325, abs=1e-3)


def test_clean_pcr_has_no_carryover() -> None:
    b = TraceBuilder(PCR_LOADS)
    b.pick_up(tip("A1"))
    for i in range(8):  # master mix first, one tip, into empty wells, from above
        b.aspirate(tip("A1"), MM, 40)
        b.dispense(tip("A1"), plate(f"A{i + 1}"), 40, height=ABOVE)
    b.drop(tip("A1"))
    for i, sample in enumerate(SAMPLES):  # then a fresh tip per sample, into the liquid
        t = tip(f"B{i + 1}")
        b.pick_up(t)
        b.aspirate(t, sample, 10)
        b.dispense(t, plate(f"A{i + 1}"), 10)
        b.drop(t)
    run = replay(b.trace())
    assert run.anomalies == ()
    assert carryover(run) == []
    assert all(a.certain for a in run.arrivals)
    for i, sample in enumerate(SAMPLES):
        assert set(run.wells[plate(f"A{i + 1}")].atoms) == {MM, sample}
        assert set(run.wells[sample].atoms) == {sample}
    assert set(run.wells[MM].atoms) == {MM}
    # The sample tips did touch the master mix in the plate: they carry it, and nothing else.
    assert set(run.tips[tip("B3")].residue) == {SAMPLES[2], MM}


# ---------------------------------------------------------------------------------------------
# The cases behind the false-positive flood of D-12
# ---------------------------------------------------------------------------------------------


def test_dispensing_from_above_into_occupied_wells_leaves_the_stock_clean() -> None:
    stock = trough("A1")
    loads = {stock: ("buffer", 10000.0)} | {
        flat(f"A{i}"): (f"sample {i}", 100.0) for i in range(1, 7)
    }
    b = TraceBuilder(loads)
    t = tip("A1")
    b.pick_up(t)
    for _ in range(2):  # two rounds: the tip goes back to the stock after visiting the samples
        b.aspirate(t, stock, 300)
        for i in range(1, 7):
            b.dispense(t, flat(f"A{i}"), 50, height=ABOVE)
    b.drop(t)
    run = replay(b.trace())
    assert run.anomalies == ()
    assert set(run.wells[stock].atoms) == {stock}
    assert [a for a in run.arrivals if a.well == stock] == []
    assert carryover(run) == []
    assert set(run.tips[t].residue) == {stock}
    assert all(
        c.verdict == "no_contact" for s in run.steps if s.op == "dispense" for c in s.contacts
    )
    assert run.wells[flat("A4")].atoms[stock].volume_ul == pytest.approx(100)


def test_air_gap_above_a_well_moves_nothing() -> None:
    stock, other = tube("A1"), tube("A2")
    b = TraceBuilder({stock: ("dye", 500.0), other: ("water", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, stock, 100)
    gap = b.aspirate(t, other, 20, height=ABOVE, parent="air_gap")  # above a different well
    inside = b.aspirate(t, other, 20, height=30.0, parent="air_gap")  # air_gap says air, anywhere
    top = b.aspirate(t, other, 20, height=37.9)  # a hand-made air gap, exactly at the well top
    b.dispense(t, flat("A1"), 160, height=ABOVE)
    run = replay(b.trace())
    assert run.anomalies == ()
    reasons = [run.steps[i].contacts[0].reason for i in (gap, inside, top)]
    assert reasons == ["air_gap", "air_gap", "tip_at_or_above_well_top"]
    for i in (gap, inside, top):
        contact = run.steps[i].contacts[0]
        assert (contact.verdict, contact.liquid_ul, contact.air_ul) == ("no_contact", 0.0, 20.0)
    assert run.wells[other] == run.well_before(other, 0)
    assert set(run.tips[t].residue) == {stock}
    # The air took room in the tip, so the 160 uL dispense balances: 100 of liquid, 60 of air.
    last = run.steps[-1].contacts[0]
    assert (last.liquid_ul, last.air_ul) == (pytest.approx(100), pytest.approx(60))
    assert run.wells[flat("A1")].volume_ul == pytest.approx(100)


def test_air_leaves_the_tip_before_the_liquid_drawn_ahead_of_it() -> None:
    stock = tube("A1")
    b = TraceBuilder({stock: ("dye", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, stock, 100)
    b.aspirate(t, stock, 10, height=ABOVE, parent="air_gap")
    first = b.dispense(t, flat("A1"), 40, height=ABOVE)  # 10 of air, then 30 of liquid
    run = replay(b.trace())
    contact = run.steps[first].contacts[0]
    assert (contact.liquid_ul, contact.air_ul) == (pytest.approx(30), pytest.approx(10))
    assert run.tips[t].liquid_ul == pytest.approx(70)
    assert run.tips[t].air_ul == 0


def test_touch_tip_is_recorded_and_moves_nothing() -> None:
    b = TraceBuilder({tube("A1"): ("dye", 500.0)})
    b.pick_up(tip("A1"))
    touch = b.touch_tip(tip("A1"), tube("A1"))
    run = replay(b.trace())
    contact = run.steps[touch].contacts[0]
    assert (contact.verdict, contact.reason) == ("no_contact", "touches_wall_only")
    assert run.tips[tip("A1")].residue == {}


def test_blow_out_empties_the_tip_into_the_well() -> None:
    stock = tube("A1")
    b = TraceBuilder({stock: ("dye", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, stock, 100)
    b.dispense(t, flat("A1"), 80, height=ABOVE)
    blow = b.blow_out(t, flat("B1"))
    run = replay(b.trace())
    assert run.anomalies == ()
    assert run.steps[blow].contacts[0].liquid_ul == pytest.approx(20)
    assert run.wells[flat("B1")].atoms[stock].volume_ul == pytest.approx(20)
    assert run.tips[t].layers == ()


# ---------------------------------------------------------------------------------------------
# Serial dilution
# ---------------------------------------------------------------------------------------------


def dilution_row(b: TraceBuilder, t: WellKey, row: str) -> None:
    for col in range(1, 6):
        b.aspirate(t, flat(f"{row}{col}"), 100)
        b.dispense(t, flat(f"{row}{col + 1}"), 100)
        for _ in range(2):
            b.aspirate(t, flat(f"{row}{col + 1}"), 50, parent="mix")
            b.dispense(t, flat(f"{row}{col + 1}"), 50, parent="mix")


def dilution_loads(rows: str) -> dict[WellKey, tuple[str, float]]:
    loads = {}
    for row in rows:
        loads[flat(f"{row}1")] = (f"stock {row}", 200.0)
        loads |= {flat(f"{row}{col}"): (f"diluent {row}{col}", 100.0) for col in range(2, 7)}
    return loads


def test_serial_dilution_halves_the_stock_at_every_step() -> None:
    b = TraceBuilder(dilution_loads("A"))
    t = tip("A1")
    b.pick_up(t)
    dilution_row(b, t, "A")
    run = replay(b.trace())
    assert run.anomalies == ()
    stock = flat("A1")
    expected = {1: 100, 2: 50, 3: 25, 4: 12.5, 5: 6.25, 6: 6.25}
    for col, amount in expected.items():
        assert run.wells[flat(f"A{col}")].atoms[stock].volume_ul == pytest.approx(amount)
    assert [run.wells[flat(f"A{c}")].volume_ul for c in range(1, 7)] == pytest.approx(
        [100, 100, 100, 100, 100, 200]
    )
    # Going down the series everything the tip has touched is also in the liquid it carries, so
    # the material arrives in bulk, each well receiving every well before it. Every mix is contact.
    assert carryover(run) == []
    for col in range(2, 7):
        upstream = {flat(f"A{c}") for c in range(1, col)}
        assert set(where(list(run.arrivals), flat(f"A{col}"))) == upstream
    assert all(c.verdict == "contact" for s in run.steps for c in s.contacts)
    # The state before an event: A3 just before the transfer into it was still pure diluent.
    into_a3 = next(a.event_index for a in run.arrivals if a.well == flat("A3"))
    assert set(run.well_before(flat("A3"), into_a3).atoms) == {flat("A3")}
    assert set(run.well_before(flat("A3"), into_a3 + 1).atoms) == {stock, flat("A2"), flat("A3")}


def test_one_tip_down_two_dilution_rows_carries_row_a_into_stock_b_and_row_b() -> None:
    b = TraceBuilder(dilution_loads("AB"))
    t = tip("A1")
    b.pick_up(t)
    dilution_row(b, t, "A")
    enters_b = len(b.events)
    dilution_row(b, t, "B")
    run = replay(b.trace())
    row_a = {flat(f"A{col}") for col in range(1, 7)}
    # The tip leaves row A carrying all six of its liquids, and deposits them in stock B.
    assert where(carryover(run), flat("B1")) == dict.fromkeys(row_a, enters_b)
    # From there they travel down row B inside the liquid: present, as a trace.
    last = run.wells[flat("B6")]
    assert row_a <= set(last.atoms)
    assert all(last.atoms[atom].volume_ul == 0.0 for atom in row_a)
    assert last.atoms[flat("B1")].volume_ul == pytest.approx(6.25)
    # The tip last met stock A's material in B5, so that is where it carried it from.
    into_b6 = run.first_arrival(flat("A1"), flat("B6"))
    assert into_b6 is not None and into_b6.source_well == flat("B5")


# ---------------------------------------------------------------------------------------------
# Tip parking
# ---------------------------------------------------------------------------------------------


def test_a_parked_tip_keeps_its_residue_and_a_dropped_tip_does_not() -> None:
    sample, buffer, other = tube("A1"), tube("A2"), tube("A3")
    b = TraceBuilder({sample: ("sample", 500.0), buffer: ("buffer", 500.0), other: ("b2", 500.0)})
    parked, fresh = tip("A1"), tip("A2")
    b.pick_up(parked)
    b.aspirate(parked, sample, 50)
    b.dispense(parked, flat("A1"), 50, height=ABOVE)
    b.drop(parked, returned=True)
    b.pick_up(fresh)
    b.aspirate(fresh, buffer, 50)
    b.dispense(fresh, flat("A1"), 50, height=ABOVE)
    b.drop(fresh)
    b.pick_up(parked)  # the same rack well: the same, used, tip
    dirty = b.aspirate(parked, buffer, 50)
    b.dispense(parked, flat("A2"), 50, height=ABOVE)
    b.drop(parked)
    again = b.pick_up(parked)  # after a real drop the rack well can only hold a new tip
    b.aspirate(parked, other, 50)
    run = replay(b.trace())
    assert run.anomalies == ()
    assert where(carryover(run), buffer) == {sample: dirty}
    assert set(run.wells[other].atoms) == {other}
    assert set(run.tips[parked].residue) == {other}
    assert run.tips[parked].picked_up_event == again
    assert run.tips[fresh].status == "dropped"
    assert set(run.tips[fresh].residue) == {buffer}


# ---------------------------------------------------------------------------------------------
# Unknown volumes
# ---------------------------------------------------------------------------------------------


def test_a_well_drawn_from_before_anything_was_put_in_it_is_an_implicit_origin() -> None:
    source, dest = tube("D1"), flat("A1")
    b = TraceBuilder()  # nothing declared, like 822 of the 833 library protocols
    t = tip("A1")
    b.pick_up(t)
    first = b.aspirate(t, source, 200)
    b.dispense(t, dest, 200, height=ABOVE)
    b.aspirate(t, source, 100)
    back = b.dispense(t, source, 50)  # some goes back: the verdict cannot be known
    b.dispense(t, dest, 50, height=ABOVE)
    b.aspirate(t, source, 30)
    run = replay(b.trace())
    assert run.anomalies == ()
    origin = run.origins[source]
    assert (origin.kind, origin.liquid_name, origin.initial_volume_ul) == ("implicit", None, None)
    assert origin.first_drawn_event == first
    # 300 out, 50 back, 30 out: the deepest it was drawn down is 300, so it held at least that.
    assert origin.min_initial_volume_ul == pytest.approx(300)
    assert run.wells[source].volume_ul is None
    assert run.wells[source].min_volume_ul == pytest.approx(20)
    assert run.well_before(source, 0).volume_ul is None  # an origin from the start, by hindsight
    assert run.well_before(source, 0).min_volume_ul == pytest.approx(300)
    assert run.well_before(source, back).min_volume_ul == pytest.approx(0)
    assert run.wells[source].atoms[source].volume_ul is None
    # What left it is known: it is the only liquid there.
    assert run.wells[dest].atoms[source].volume_ul == pytest.approx(250)
    assert run.wells[dest].volume_ul == pytest.approx(250)
    verdicts = [(s.contacts[0].verdict, s.contacts[0].reason) for s in run.steps if s.contacts]
    assert verdicts[0] == ("contact", "draws_liquid_volume_unknown")
    assert verdicts[3] == ("unknown", "volume_unknown")


def test_a_plate_that_arrives_holding_samples_is_found_by_what_is_drawn_out_of_it() -> None:
    """The library's commonest shape: nothing declared, reagent is added to each well of a plate,
    then more is drawn out than was put in. "A well that gives more than it ever got was holding
    something": each such well is an origin from event 0, so one tip through all of them shows."""
    reagent = trough("A1")
    samples = [plate("A1"), plate("A2"), plate("A3")]
    b = TraceBuilder()
    t = tip("A1")
    b.pick_up(t)
    added, mixed = [], []
    for well in samples:
        b.aspirate(t, reagent, 8)
        added.append(b.dispense(t, well, 8))
        mixed.append(b.aspirate(t, well, 45, parent="mix"))  # 45 out of a well that was given 8
        b.dispense(t, well, 45, parent="mix")
    run = replay(b.trace())
    assert run.anomalies == ()  # no "aspirate_exceeds_volume": the well is not short, it was full
    assert set(run.origins) == {reagent, *samples}
    for well, add, mix in zip(samples, added, mixed, strict=True):
        origin = run.origins[well]
        assert (origin.kind, origin.first_drawn_event) == ("implicit", mix)
        assert origin.min_initial_volume_ul == pytest.approx(45 - 8)
        assert run.well_before(well, 0).volume_ul is None  # known by hindsight, from the start
        assert set(run.well_before(well, 0).atoms) == {well}
        # The dispense before the draw is judged honestly: we do not know where the surface was.
        contact = run.steps[add].contacts[0]
        assert (contact.verdict, contact.reason) == ("unknown", "volume_unknown")
    # One tip through three samples: each later sample receives the earlier ones.
    assert set(run.wells[samples[0]].atoms) == {samples[0], reagent}
    assert set(run.wells[samples[2]].atoms) == {*samples, reagent}
    # Sample 1 gets there twice over: the dirty tip put it in the reagent trough, so it is a trace
    # in the very liquid dispensed into sample 2, whether or not the tip then touched.
    second = run.first_arrival(samples[0], samples[1])
    assert second is not None
    assert (second.mode, second.volume_ul, second.certain) == ("bulk", 0.0, True)
    assert (second.event_index, second.source_well) == (added[1], samples[0])
    # And the reagent trough is dirtied with sample 1 when the tip goes back to it.
    dirtied = run.first_arrival(samples[0], reagent)
    assert dirtied is not None and (dirtied.mode, dirtied.certain) == ("carryover", True)
    assert dirtied.event_index == added[1] - 1


def test_a_protocol_that_declares_its_liquids_has_said_what_is_on_the_deck() -> None:
    """Two regimes. The robot puts 30 uL in a well and a consolidate then asks it for 40. If the
    protocol declared its liquids, the well was empty and this is its own shortfall. If it declared
    nothing, the well may well have arrived full, like most plates in the public library."""
    dye, well, out = tube("A1"), flat("B1"), tube("A2")

    def protocol(loads: dict[WellKey, tuple[str, float]]) -> Run:
        b = TraceBuilder(loads)
        t = tip("A1")
        b.pick_up(t)
        b.aspirate(t, dye, 30)
        b.dispense(t, well, 30, height=ABOVE)
        b.aspirate(t, well, 40, height=0.5, parent="consolidate")
        b.dispense(t, out, 40, height=ABOVE)
        return replay(b.trace())

    declared = protocol({dye: ("dye", 1200.0)})
    assert set(declared.origins) == {dye}
    assert [a.kind for a in declared.anomalies] == ["aspirate_exceeds_volume"]
    assert set(declared.wells[out].atoms) == {dye}

    silent = protocol({})
    assert set(silent.origins) == {dye, well}
    assert silent.anomalies == ()
    assert set(silent.wells[out].atoms) == {dye, well}


def test_a_declared_well_that_runs_short_stays_an_anomaly() -> None:
    full, empty = tube("A1"), tube("A2")
    b = TraceBuilder({full: ("dye", 300.0), empty: ("nothing", 0.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, full, 350)  # the protocol said 300 uL: it is wrong somewhere, and we say so
    b.dispense(t, empty, 80, height=ABOVE)  # 50 of air, then 30 of liquid
    b.aspirate(t, empty, 40, height=0.3)  # declared empty (`load_empty`), given 30, asked for 40
    run = replay(b.trace())
    assert [a.kind for a in run.anomalies] == ["aspirate_exceeds_volume"] * 2
    assert set(run.origins) == {full}


def test_a_well_can_be_named_an_implicit_origin_by_the_caller() -> None:
    sample = plate("A1")
    b = TraceBuilder({tube("A1"): ("reagent", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, tube("A1"), 20)
    add = b.dispense(t, sample, 20)
    trace = b.trace()
    assert sample not in replay(trace).origins  # nothing in the trace shows it held anything
    run = replay(trace, implicit_origins=[sample])
    assert run.origins[sample].kind == "implicit"
    assert run.origins[sample].first_drawn_event is None
    assert run.steps[add].contacts[0].verdict == "unknown"
    assert set(run.tips[t].residue) == {tube("A1"), sample}
    assert not run.tips[t].residue[sample].certain


def test_overflow_is_noted_once_and_not_inferred_from_an_implicit_origins_floor() -> None:
    wash, beads, waste = trough("A1"), plate("A1"), trough("A12")
    b = TraceBuilder()
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, wash, 90)
    b.dispense(t, beads, 90, height=ABOVE)
    b.aspirate(t, beads, 150)  # supernatant removal asks for extra, to be sure to get it all
    b.dispense(t, waste, 150, height=ABOVE)
    run = replay(b.trace())
    # The floor says the well held 60 uL, so 150 uL after the wash, in a 100 uL well. But the
    # extra may have been air. Only what the robot itself put in counts towards overflow.
    assert run.origins[beads].min_initial_volume_ul == pytest.approx(60)
    assert run.anomalies == ()

    b = TraceBuilder({wash: ("wash", 5000.0)})
    b.pick_up(t)
    for _ in range(3):
        b.aspirate(t, wash, 60)
        b.dispense(t, beads, 60, height=ABOVE)
    run = replay(b.trace())
    assert [(a.kind, a.event_index, a.amount_ul) for a in run.anomalies] == [("overflow", 4, 20.0)]
    assert run.wells[beads].volume_ul == pytest.approx(180)  # the volume is kept, not clipped


def test_liquid_dispensed_into_an_unknown_well_certainly_arrives_whatever_the_contact() -> None:
    sample, reagent = tube("A1"), tube("D1")
    b = TraceBuilder({sample: ("sample", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, reagent, 100)  # reagent becomes an implicit origin
    b.dispense(t, flat("A1"), 100, height=ABOVE)
    b.aspirate(t, sample, 50)
    maybe = b.dispense(t, reagent, 50, height=20.0)  # into the unknown well, below its top
    run = replay(b.trace())
    # The liquid itself certainly arrived; whether the tip touched is what is not known.
    arrivals = [a for a in run.arrivals if (a.atom, a.well) == (sample, reagent)]
    assert [(a.mode, a.certain, a.event_index) for a in arrivals] == [("bulk", True, maybe)]
    assert run.steps[maybe].contacts[0].verdict == "unknown"
    # The tip certainly carries the reagent: it drew it at event 1.
    assert run.tips[t].residue[reagent].certain
    assert run.tips[t].residue[reagent].since_event == 1


def test_uncertain_carryover_is_marked_and_later_made_certain() -> None:
    sample, reagent, other = tube("A1"), tube("D1"), tube("D2")
    b = TraceBuilder({sample: ("sample", 500.0)})
    t = tip("A1")
    b.pick_up(t)
    b.aspirate(t, reagent, 100)
    b.dispense(t, flat("A1"), 100, height=ABOVE)
    b.aspirate(t, other, 100)
    b.dispense(t, flat("A2"), 100, height=ABOVE)
    b.aspirate(t, sample, 50)
    maybe = b.dispense(t, reagent, 0, height=20.0)  # dips, perhaps, and puts nothing in
    b.dispense(t, flat("A3"), 50, height=ABOVE)
    sure = b.aspirate(t, reagent, 10)
    run = replay(b.trace())
    got = [(a.mode, a.certain, a.event_index) for a in run.arrivals if a.well == reagent]
    assert sorted(got) == sorted(
        [("carryover", False, maybe)] * 2 + [("carryover", True, sure)] * 2
    )
    assert run.well_before(reagent, sure).atoms[sample].certain is False
    assert run.wells[reagent].atoms[sample].certain is True
    assert run.wells[reagent].atoms[sample].since_event == maybe


def test_aspirating_above_the_modelled_surface_moves_liquid_but_is_not_called_contact() -> None:
    sample = tube("A1")
    b = TraceBuilder({sample: ("sample", 20.0)})  # 20 uL in an 8.7 mm column is 0.34 mm deep
    t = tip("A1")
    b.pick_up(t)
    event = b.aspirate(t, sample, 10)
    b.dispense(t, flat("A1"), 10, height=ABOVE)
    run = replay(b.trace())
    contact = run.steps[event].contacts[0]
    assert (contact.verdict, contact.reason) == ("unknown", "tip_above_column_height")
    assert contact.liquid_ul == pytest.approx(10)
    assert [a.kind for a in run.anomalies] == ["aspirate_above_liquid"]
    arrival = run.first_arrival(sample, flat("A1"))
    assert arrival is not None and not arrival.certain


def _with_geometry(trace: Trace, labware_id: str, geometry: WellGeometry) -> Trace:
    """The same trace with every well of one labware given `geometry`."""
    labware = [
        replace(lw, wells=dict.fromkeys(lw.wells, geometry)) if lw.labware_id == labware_id else lw
        for lw in trace.deck.labware
    ]
    return replace(trace, deck=replace(trace.deck, labware=labware))


def test_aspirating_above_the_surface_of_a_flat_well_draws_air() -> None:
    sample = flat("A1")
    b = TraceBuilder({sample: ("sample", 20.0)})  # 20 uL in a 6.86 mm column is 0.54 mm deep
    t = tip("A1")
    b.pick_up(t)
    event = b.aspirate(t, sample, 10)
    b.dispense(t, plate("A1"), 10, height=ABOVE)
    trace = _with_geometry(b.trace(), FLAT_ID, replace(FLAT, bottom_shape="flat"))
    run = replay(trace)
    contact = run.steps[event].contacts[0]
    assert (contact.verdict, contact.reason) == ("no_contact", "tip_above_surface")
    assert contact.surface_mm == pytest.approx(20 / (math.pi * 3.43**2), abs=0.01)
    assert (contact.liquid_ul, contact.air_ul) == (0.0, 10.0)
    assert [a.kind for a in run.anomalies] == ["aspirate_above_liquid"]
    assert run.wells[sample].volume_ul == pytest.approx(20)  # nothing left the well
    assert run.first_arrival(sample, plate("A1")) is None  # the plate got 10 uL of air
    assert run.wells[plate("A1")].volume_ul == 0


def test_a_volume_to_height_table_lifts_the_liquid_in_a_cone() -> None:
    # A cone whose first 50 uL reach 5 mm: 20 uL sits at 3 mm, well above a tip at 1 mm.
    cone = replace(TUBE, bottom_shape="v", height_at_ul=[(0, 0), (10, 2), (50, 5), (1500, 37.9)])
    sample = tube("A1")
    b = TraceBuilder({sample: ("sample", 20.0)})
    t = tip("A1")
    b.pick_up(t)
    low = b.aspirate(t, sample, 5, height=LOW)
    high = b.aspirate(t, sample, 5, height=4.0)  # above the 2.9 mm the 15 uL left reach
    run = replay(_with_geometry(b.trace(), RACK_ID, cone))
    assert run.steps[low].contacts[0].reason == "tip_below_surface"
    assert run.steps[low].contacts[0].surface_mm == pytest.approx(2 + 3 * 10 / 40)
    assert run.steps[high].contacts[0].reason == "tip_above_surface"
    assert run.steps[high].contacts[0].surface_mm == pytest.approx(2 + 3 * 5 / 40)
    assert run.wells[sample].volume_ul == pytest.approx(15)


def test_surface_from_a_table_is_clamped_to_its_ends() -> None:
    cone = replace(TUBE, height_at_ul=[(0, 0), (10, 2), (50, 5), (1500, 37.9)])
    assert surface_mm(cone, 0) == 0
    assert surface_mm(cone, 1500) == pytest.approx(37.9)
    assert surface_mm(cone, 5000) == pytest.approx(37.9)
    assert surface_mm(cone, 10) == pytest.approx(2)
    assert surface_mm(TUBE, 10) == pytest.approx(10 / (math.pi * 4.35**2))  # no table: a column


# ---------------------------------------------------------------------------------------------
# Multi-channel
# ---------------------------------------------------------------------------------------------


def test_eight_channels_from_one_reservoir_well_into_a_plate_column() -> None:
    stock = trough("A1")
    samples = {flat(f"{row}1"): (f"sample {row}", 100.0) for row in ROWS}
    b = TraceBuilder({stock: ("buffer", 5000.0)} | samples)
    tips = [tip(f"{row}1") for row in ROWS]
    column = [flat(f"{row}1") for row in ROWS]
    b.pick_up(tips)
    b.aspirate(tips, [stock] * 8, 50)
    b.dispense(tips, column, 50)  # into the samples: each tip touches its own sample only
    back = b.aspirate(tips, [stock] * 8, 50)  # all eight dirty tips enter the one reservoir well
    run = replay(b.trace())
    assert run.anomalies == ()
    assert run.wells[stock].volume_ul == pytest.approx(5000 - 800)
    assert len(run.steps[back].contacts) == 8
    assert where(carryover(run), stock) == dict.fromkeys(column, back)
    by_tip = {a.atom: a.via_tip for a in carryover(run) if a.well == stock}
    assert by_tip == dict(zip(column, tips, strict=True))
    for well in column:
        assert set(run.wells[well].atoms) == {well, stock}
        assert run.wells[well].volume_ul == pytest.approx(150)


def test_channels_dispensing_into_one_well_are_judged_against_the_final_surface() -> None:
    stock = trough("A1")
    b = TraceBuilder({stock: ("buffer", 5000.0)})
    tips = [tip(f"{row}1") for row in ROWS]
    b.pick_up(tips)
    b.aspirate(tips, [stock] * 8, 100)
    # 8 x 100 uL into an empty trough well of 584 mm2 is 1.37 mm: every tip at 1 mm is wetted,
    # the first channel too, though its own 100 uL alone would be only 0.17 mm.
    event = b.dispense(tips, [trough("A2")] * 8, 100, height=LOW)
    run = replay(b.trace())
    assert [c.verdict for c in run.steps[event].contacts] == ["contact"] * 8
    assert run.wells[trough("A2")].volume_ul == pytest.approx(800)


# ---------------------------------------------------------------------------------------------
# Anomalies: recorded, never raised
# ---------------------------------------------------------------------------------------------


def test_anomalies_are_collected_and_the_replay_finishes() -> None:
    stock = tube("A1")
    b = TraceBuilder({stock: ("dye", 100.0)})
    t = tip("A1")
    b.aspirate(None, stock, 10)  # no tip on
    b.aspirate(t, stock, 150)  # a tip that was never picked up; more than the well holds
    b.aspirate(t, stock, 10)  # the well is now empty
    b.dispense(t, plate("A1"), 300, height=ABOVE)  # more than the tip holds
    b.pick_up(tip("A2"))
    b.aspirate(tip("A2"), tube("D1"), 150)
    b.dispense(tip("A2"), plate("A1"), 50, height=ABOVE)  # 150 uL in a 100 uL well
    b.aspirate(tip("A2"), WellKey("9:mystery", "A1"), 10)  # labware the deck header lacks
    b.drop(tip("A2"))  # with 110 uL still in it
    b.other("thermocycler_profile")
    run = replay(b.trace())
    assert [(a.event_index, a.kind) for a in run.anomalies] == [
        (0, "no_tip"),
        (1, "tip_not_picked_up"),
        (1, "aspirate_exceeds_volume"),
        (2, "aspirate_from_empty_well"),
        (3, "dispense_exceeds_held"),
        (6, "overflow"),
        (7, "well_not_on_deck"),
        (8, "tip_dropped_with_liquid"),
        (9, "profile_not_modelled"),
    ]
    amounts = {a.kind: a.amount_ul for a in run.anomalies}
    assert amounts["aspirate_exceeds_volume"] == pytest.approx(50)
    assert amounts["dispense_exceeds_held"] == pytest.approx(140)
    assert amounts["overflow"] == pytest.approx(50)
    assert amounts["tip_dropped_with_liquid"] == pytest.approx(110)
    # Over-drawing takes what is there and the rest is air.
    assert run.steps[1].contacts[0].liquid_ul == pytest.approx(100)
    assert run.steps[1].contacts[0].air_ul == pytest.approx(50)
    assert run.wells[stock].volume_ul == 0
    assert set(run.wells[stock].atoms) == {stock}  # an emptied well still has its film


def test_a_well_declared_empty_is_not_an_origin() -> None:
    from provette.model import Deck, LiquidLoad, Trace, WellKey

    well = WellKey("1:plate", "A1")
    deck = Deck("p.py", "2.27", "8.8.2", [], [], [LiquidLoad(well, "", None, 0.0, 3)])
    assert replay(Trace(deck, [])).origins == {}
