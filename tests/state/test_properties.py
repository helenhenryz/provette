"""Layer 1 of the validation loop: invariants of the replay on random, well-formed event streams.

A stream is drawn as a list of small integer tuples and turned into legal events by `build`: a tip
is picked up before it acts, never holds more than 300 uL, and never dispenses more than it holds.
Everything else is left free on purpose: any well, declared or not; any height, in the liquid,
above it, at the top; air gaps; tips returned to the rack and picked up again; tips dropped with
liquid in them; aspirates of more than a well holds.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from provette.model import Trace, WellKey
from provette.state import Run, replay
from tests.state.builder import ABOVE, FLAT_ID, TraceBuilder, flat, tip, trough, tube

DECLARED = {tube("A1"): ("a", 300.0), tube("A2"): ("b", 60.0), trough("A1"): ("c", 5000.0)}
UNDECLARED = [tube("D1"), tube("D2"), flat("A1"), flat("A2"), trough("A2")]
WELLS = [*DECLARED, *UNDECLARED, tube("D1"), flat("A1")]  # the repeats make reuse likelier
TIPS = [tip(f"A{i}") for i in range(1, 7)]
HEIGHTS = [0.0, 1.0, 3.0, 9.0, 10.67, ABOVE]  # 10.67 mm is exactly the top of a flat well
CAPACITY = 300.0

Code = tuple[int, int, int, int]
Stream = tuple[bool, list[Code]]
# The flag picks the regime: a protocol that declares its liquids, or, like most of the public
# library, one that declares nothing, where every well may turn out to have been holding something.
codes = st.tuples(
    st.booleans(), st.lists(st.tuples(*[st.integers(0, 11)] * 4), min_size=12, max_size=60)
)


def build(drawn: Stream) -> Trace:
    declares, stream = drawn
    b = TraceBuilder(DECLARED if declares else {})
    on: WellKey | None = None  # the tip on the pipette
    held = 0.0
    for op, x, y, z in stream:
        well, height = WELLS[x % len(WELLS)], HEIGHTS[z % len(HEIGHTS)]
        if on is None:
            on = TIPS[x % len(TIPS)]
            b.pick_up(on)
        elif op <= 3:
            volume = min((y + 1) * 12.5, CAPACITY - held)
            b.aspirate(on, well, volume, height, parent="air_gap" if z == 11 else None)
            held += volume
        elif op <= 6:
            volume = held if y > 8 else held * y / 8
            b.dispense(on, well, volume, height, parent="mix" if z == 11 else None)
            held -= volume
        elif op == 7:
            b.blow_out(on, well, height)
            held = 0.0
        elif op == 8:
            b.touch_tip(on, well)
        elif op == 9:
            b.drop(on, returned=y % 2 == 0)
            on, held = None, 0.0
        elif op == 10:
            b.delay(30.0 * y)
        else:
            b.set_temperature(FLAT_ID, 4.0 + y)
    return b.trace()


def prefix(trace: Trace, length: int) -> Trace:
    return Trace(deck=trace.deck, events=trace.events[:length])


def total_ul(run: Run) -> float:
    in_wells = sum(well.min_volume_ul for well in run.wells.values())
    in_tips = sum(t.liquid_ul for t in run.tips.values())
    discarded = sum(a.amount_ul or 0 for a in run.anomalies if a.kind == "tip_dropped_with_liquid")
    return in_wells + in_tips + discarded


def initial_ul(run: Run) -> float:
    return sum(origin.min_initial_volume_ul for origin in run.origins.values())


@settings(max_examples=150, deadline=None)
@given(codes)
def test_volume_is_conserved(stream: Stream) -> None:
    trace = build(stream)
    for length in range(len(trace.events) + 1):
        run = replay(prefix(trace, length))
        # Liquid is in a well, in a tip, or went out in a discarded tip. For a well of unknown
        # volume the lower bound is counted, on both sides.
        assert total_ul(run) == pytest.approx(initial_ul(run), abs=1e-6)
        for states in run.history.values():
            assert all(state.min_volume_ul >= -1e-6 for _, state in states)
            assert all(s.volume_ul is None or s.volume_ul == s.min_volume_ul for _, s in states)
        for well, origin in run.origins.items():
            if origin.kind == "implicit":  # the bound is tight: the well does get that low
                lowest = min(state.min_volume_ul for _, state in run.history[well])
                assert lowest == pytest.approx(0, abs=1e-6)
    # Within a well the atoms add up to the volume, when every amount is known.
    for state in run.wells.values():
        amounts = [presence.volume_ul for presence in state.atoms.values()]
        if state.volume_ul is not None and None not in amounts:
            assert sum(a for a in amounts if a is not None) == pytest.approx(
                state.volume_ul, abs=1e-6
            )


@settings(max_examples=150, deadline=None)
@given(codes)
def test_provenance_only_grows(stream: Stream) -> None:
    trace = build(stream)
    run = replay(trace)
    for well in run.wells:
        for i in range(len(trace.events)):
            old, new = run.well_before(well, i).atoms, run.well_before(well, i + 1).atoms
            assert set(old) <= set(new)
            for atom, was in old.items():
                assert not (was.mode == "bulk" and new[atom].mode == "carryover")
                assert new[atom].certain or not was.certain
                assert new[atom].since_event == was.since_event
    # Prefixes are told the whole run's implicit origins: without that, a later event can prove a
    # well was holding something all along and lower an earlier certainty (README, "hindsight").
    known = [key for key, origin in run.origins.items() if origin.kind == "implicit"]
    runs = [
        replay(prefix(trace, length), implicit_origins=known)
        for length in range(len(trace.events) + 1)
    ]
    for earlier, later in zip(runs, runs[1:], strict=False):
        for key, was in earlier.tips.items():
            now = later.tips[key]
            if now.picked_up_event == was.picked_up_event:  # else a new tip from the same place
                assert set(was.residue) <= set(now.residue)
                assert all(now.residue[a].certain or not r.certain for a, r in was.residue.items())


@settings(max_examples=150, deadline=None)
@given(codes)
def test_a_fresh_tip_carries_nothing(stream: Stream) -> None:
    trace = build(stream)
    gone: dict[WellKey, bool] = {}  # tip -> it was dropped for good (True) or parked (False)
    for event in trace.events:
        key = event.targets[0].tip if event.targets else None
        if event.op == "drop_tip" and key is not None:
            gone[key] = not event.returned
        if event.op == "pick_up_tip" and key is not None:
            state = replay(prefix(trace, event.index + 1)).tips[key]
            assert state.status == "in_use"
            if gone.get(key, True):
                assert state.residue == {} and state.layers == ()
                assert state.picked_up_event == event.index


def implicit(run: Run) -> set[WellKey]:
    return {well for well, origin in run.origins.items() if origin.kind == "implicit"}


@settings(max_examples=100, deadline=None)
@given(codes)
def test_replay_is_deterministic_and_a_prefix_replays_to_a_prefix(stream: Stream) -> None:
    """The prefix property is conditional, and says so: implicit origins are found by hindsight.

    A prefix of the trace may end before the event that proves a well was holding something, and
    then replays that well as empty where the whole run replays it as an origin. So: told the
    whole run's implicit origins, a prefix replays to a prefix of the whole run's steps. Untold,
    it finds a subset of them, never an origin the whole run does not have.
    """
    trace = build(stream)
    run = replay(trace)
    assert replay(trace) == run
    assert replay(trace, implicit_origins=implicit(run)) == run  # it is told nothing new
    assert len(run.steps) == len(trace.events)
    for length in range(len(trace.events) + 1):
        assert implicit(replay(prefix(trace, length))) <= implicit(run)
        part = replay(prefix(trace, length), implicit_origins=implicit(run))
        assert part.steps == run.steps[:length]
        # And the state the full run remembers for "just before event `length`" is the state the
        # prefix ends in. Only the lower bound of an unknown volume may differ: it looks ahead.
        for well, state in part.wells.items():
            before = run.well_before(well, length)
            if state.volume_ul is None:
                before = replace(before, min_volume_ul=state.min_volume_ul)
            assert before == state


@settings(max_examples=150, deadline=None)
@given(codes)
def test_a_well_that_gives_more_than_it_got_was_holding_something(stream: Stream) -> None:
    """An implicit origin is one from event 0 and never runs short. Where nothing is declared,
    no well runs short at all; where liquids are declared, the robot's own wells still can."""
    declares = stream[0]
    trace = build(stream)
    run = replay(trace)
    kinds = {"aspirate_exceeds_volume", "aspirate_from_empty_well"}
    short = {a.well for a in run.anomalies if a.kind in kinds}
    assert not short & implicit(run)
    for well in implicit(run):
        assert run.well_before(well, 0).volume_ul is None
        assert set(run.well_before(well, 0).atoms) == {well}
        first = run.origins[well].first_drawn_event
        assert first is not None
        if declares:  # then only a well the robot had put nothing into can be found
            assert not run.well_before(well, first).received_liquid
    if declares:
        return
    # Nothing declared: no well ever runs short, and every well that is not an origin really did
    # give no more than it got, at every step.
    assert not short
    for well in set(WELLS) - implicit(run):
        balance = 0.0
        for step in run.steps:
            for contact in step.contacts:
                if contact.well == well:
                    balance += contact.liquid_ul if step.op != "aspirate" else -contact.liquid_ul
                    assert balance >= -1e-6


@settings(max_examples=150, deadline=None)
@given(codes)
def test_every_atom_in_a_well_is_explained_by_arrivals_back_to_its_origin(
    stream: Stream,
) -> None:
    run = replay(build(stream))
    for arrival in run.arrivals:
        now = run.well_before(arrival.well, arrival.event_index + 1).atoms[arrival.atom]
        assert (arrival.mode == "bulk") <= (now.mode == "bulk")
        assert arrival.certain <= now.certain
    for well, state in run.wells.items():
        for atom, presence in state.atoms.items():
            assert atom in run.origins
            if atom == well:
                assert presence.since_event is None
                continue
            first = run.first_arrival(atom, well)
            assert first is not None and first.event_index == presence.since_event
            here, latest = well, len(run.steps)
            for _ in range(len(run.steps) + 1):  # walk back; it must end, at the origin
                if here == atom:
                    break
                step = run.first_arrival(atom, here)
                assert step is not None and step.event_index <= latest
                # The well the tip took it from did hold it by then.
                assert atom in run.well_before(step.source_well, step.event_index + 1).atoms
                here, latest = step.source_well, step.event_index
            assert here == atom
            assert run.material_temperature(atom, well, len(run.steps)) != []


transfers = st.lists(
    st.tuples(st.integers(0, len(WELLS) - 1), st.integers(0, len(WELLS) - 1), st.integers(1, 24)),
    max_size=40,
)


@settings(max_examples=150, deadline=None)
@given(transfers)
def test_fresh_tips_and_dispensing_from_above_never_carry_anything_over(
    moves: list[tuple[int, int, int]],
) -> None:
    b = TraceBuilder(DECLARED)
    for n, (source, dest, volume) in enumerate(moves):
        fresh = tip(f"{'ABCDEFGH'[n // 12]}{n % 12 + 1}")
        b.pick_up(fresh)
        b.aspirate(fresh, WELLS[source], volume * 12.5)
        b.dispense(fresh, WELLS[dest], volume * 12.5, height=ABOVE)
        b.blow_out(fresh, WELLS[dest])
        b.drop(fresh)
    run = replay(b.trace())
    assert [a for a in run.arrivals if a.mode == "carryover"] == []
    assert all(presence.mode == "bulk" for w in run.wells.values() for presence in w.atoms.values())
