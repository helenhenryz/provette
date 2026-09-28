"""Roots and consequences, on traces built by hand: no simulator, so these run in milliseconds.

The buggy PCR set-up is the case the project started from. The others pin down the ideas the
contamination rules share (see `provette/rules/common.py`).
"""

from __future__ import annotations

from dataclasses import replace

from provette.model import Trace
from provette.rules import Finding, run_rules
from provette.rules.common import Facts
from provette.state import replay
from tests.state.builder import ABOVE, TraceBuilder, plate, tip, tube

SAMPLES = ["B1", "B2", "B3", "B4"]


def _check(builder: TraceBuilder) -> list[Finding]:
    trace = Trace(builder.deck, builder.events)
    return run_rules(trace, replay(trace))


def _in_a_loop(builder: TraceBuilder, first: int, body: int, at_line: int) -> Trace:
    """The builder gives every event a line of its own. Here events `first`, `first + body`...
    share a line, as the iterations of a loop `body` statements long do."""
    events = []
    for event in builder.events:
        line = at_line + (event.index - first) % body if event.index >= first else event.index
        events.append(replace(event, line=line, stack=[f"run:{line}"]))
    return Trace(builder.deck, events)


def _buggy_pcr() -> TraceBuilder:
    loads = {tube("A1"): ("master mix", 1000.0)}
    loads.update({tube(name): (f"sample {n}", 100.0) for n, name in enumerate(SAMPLES, 1)})
    b = TraceBuilder(loads)
    b.pick_up(tip("A1"))
    for column, name in enumerate(SAMPLES, 1):
        b.aspirate(tip("A1"), tube(name), 20)
        b.dispense(tip("A1"), plate(f"A{column}"), 20)
        b.aspirate(tip("A1"), tube("A1"), 40)
        b.dispense(tip("A1"), plate(f"A{column}"), 40)
    b.drop(tip("A1"))
    return b


def test_buggy_pcr_roots_are_the_tip_going_into_tubes_not_the_liquid_flowing_out() -> None:
    b = _buggy_pcr()
    trace = Trace(b.deck, b.events)
    facts = Facts(trace, replay(trace))
    assert {root.mode for root in facts.roots} == {"carryover"}
    # every root is in a tube; what reached the plate wells came inside liquid: consequences
    assert {root.well.labware_id for root in facts.roots} == {tube("A1").labware_id}
    traces_in_plate = [
        a
        for a in facts.run.arrivals
        if a.well == plate("A3") and a.mode == "bulk" and not a.volume_ul
    ]
    assert traces_in_plate, "the state reports traces carried inside liquid as bulk arrivals of 0"


def test_buggy_pcr_gives_one_finding_per_root_line() -> None:
    trace = _in_a_loop(_buggy_pcr(), first=1, body=4, at_line=30)
    findings = run_rules(trace, replay(trace))
    # the plate has four reaction wells and no no-template well, so the control note is there
    # too; and the proposed declared rule notes the sample tip in the master mix (line 32)
    assert sorted(f.rule_id for f in findings if f.severity == "note") == [
        "NO-NEGATIVE-CONTROL",
        "NO-SAMPLE-INTO-REAGENT-WELL",
    ]
    tubes, master_mix = [f for f in findings if f.severity != "note"]
    assert [(f.rule_id, f.line) for f in (tubes, master_mix)] == [
        ("CONTAM-STOCK", 30),
        ("CONTAM-STOCK", 32),
    ]
    assert [w.well for w in master_mix.wells] == ["A1"]
    assert [w.well for w in master_mix.downstream.wells] == ["A2", "A3", "A4"]
    assert [o.event_index for o in master_mix.occurrences] == [3, 7, 11, 15]
    assert [w.well for w in tubes.wells] == ["B2", "B3", "B4"]
    assert master_mix.severity == tubes.severity == "error"


def test_a_clean_tip_through_a_dirty_stock_is_a_consequence_not_a_new_root() -> None:
    """Tip 1 dirties the master mix. Tip 2 is fresh, draws master mix, touches the liquid in a
    plate well and then goes into the water tube. It passes on a trace of sample 1: that
    belongs to the first finding. What tip 2 really carries into the water is master mix."""
    b = TraceBuilder(
        {
            tube("A1"): ("master mix", 1000.0),
            tube("B1"): ("sample 1", 100.0),
            tube("C1"): ("water", 1000.0),
        }
    )
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("B1"), 20)
    b.dispense(tip("A1"), plate("A1"), 20)
    b.aspirate(tip("A1"), tube("A1"), 40)  # root: sample 1 into the master mix
    b.dispense(tip("A1"), plate("A1"), 40)
    b.drop(tip("A1"))
    b.pick_up(tip("B1"))
    b.aspirate(tip("B1"), tube("A1"), 50)
    b.dispense(tip("B1"), plate("A2"), 50)  # 50 uL in a PCR well: the tip is in the liquid
    b.aspirate(tip("B1"), tube("C1"), 50)  # root: master mix into the water
    b.dispense(tip("B1"), plate("A2"), 50)
    b.drop(tip("B1"))

    findings = [f for f in _check(b) if f.rule_id == "CONTAM-STOCK"]
    assert [(f.line, [w.well for w in f.wells]) for f in findings] == [(4, ["A1"]), (10, ["C1"])]
    first, second = findings
    assert [w.well for w in first.downstream.wells] == ["A2", "C1"]  # the water got the trace too
    assert "master mix" in second.explanation and "sample 1" not in second.explanation


def test_a_tip_put_back_in_the_rack_is_still_dirty_when_picked_up_again() -> None:
    b = TraceBuilder({tube("A1"): ("buffer", 1000.0), tube("B1"): ("sample 1", 100.0)})
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("B1"), 20)
    b.dispense(tip("A1"), plate("A1"), 20, height=ABOVE)
    b.drop(tip("A1"), returned=True)
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("A1"), 20)
    b.dispense(tip("A1"), plate("A2"), 20, height=ABOVE)
    b.drop(tip("A1"))
    (finding,) = _check(b)
    assert (finding.rule_id, finding.line, finding.severity) == ("CONTAM-STOCK", 6, "error")
    assert [w.well for w in finding.downstream.wells] == ["A2"]


def test_a_new_tip_from_the_same_rack_position_is_clean() -> None:
    b = TraceBuilder({tube("A1"): ("buffer", 1000.0), tube("B1"): ("sample 1", 100.0)})
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("B1"), 20)
    b.dispense(tip("A1"), plate("A1"), 20, height=ABOVE)
    b.drop(tip("A1"))  # in the trash; the rack was refilled
    b.pick_up(tip("A1"))
    b.aspirate(tip("A1"), tube("A1"), 20)
    b.dispense(tip("A1"), plate("A2"), 20, height=ABOVE)
    b.drop(tip("A1"))
    assert _check(b) == []


def test_an_uncertain_contact_lowers_the_finding_one_level_and_says_so() -> None:
    """20 uL declared in a 1.5 mL tube: as a straight column that is 0.3 mm deep, and the tip is
    at 1 mm. The real tube is conical, so the state calls the contact unknown (DECISIONS D-13).
    With 1000 uL in the tube the same steps are certain."""

    def steps(buffer_ul: float) -> list[Finding]:
        b = TraceBuilder({tube("A1"): ("buffer", buffer_ul), tube("B1"): ("sample 1", 500.0)})
        b.pick_up(tip("A1"))
        b.aspirate(tip("A1"), tube("B1"), 20)
        b.dispense(tip("A1"), plate("A1"), 20, height=ABOVE)
        b.aspirate(tip("A1"), tube("A1"), 20)
        b.dispense(tip("A1"), plate("A2"), 20, height=ABOVE)
        b.drop(tip("A1"))
        return _check(b)

    (sure,) = steps(1000.0)
    (unsure,) = steps(20.0)
    assert (sure.severity, sure.certain) == ("error", True)
    assert (unsure.severity, unsure.certain) == ("warning", False)
    assert "could not tell for sure" in unsure.explanation
    assert sure.fingerprint == unsure.fingerprint  # the same finding, held less firmly


def test_the_same_helper_line_reached_two_ways_is_two_findings() -> None:
    """The grouping key is the whole stack, not the innermost line."""
    looped = _in_a_loop(_buggy_pcr(), first=1, body=4, at_line=30)
    events = [
        replace(e, stack=["run:50" if e.index < 9 else "run:60", f"helper:{e.line}"])
        for e in looped.events
    ]
    findings = [
        f
        for f in run_rules(Trace(looped.deck, events), replay(looped))
        if f.rule_id == "CONTAM-STOCK"
    ]
    assert sorted((f.line, f.stack[0]) for f in findings) == [
        (30, "run:50"),
        (30, "run:60"),
        (32, "run:50"),
        (32, "run:60"),
    ]
    assert len({f.fingerprint for f in findings}) == 4
