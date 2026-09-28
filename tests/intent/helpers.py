"""Hand-built runs for the intent tests: a PCR set-up on the fixed deck of tests/state/builder."""

from __future__ import annotations

from typing import Any

from provette.intent.spec import PlateMap, platemap_from_dict
from provette.model import Trace
from tests.state.builder import ABOVE, TraceBuilder, plate, tip, tube

TUBES = ["A2", "B2", "C2", "D2"]
DESTS = ["A1", "B1", "C1", "D1"]


def pcr_trace(
    *,
    mix_declared: float = 200,
    sample_ul: float = 5,
    sample_order: tuple[int, ...] = (0, 1, 2, 3),
    dests: tuple[str, ...] = tuple(DESTS),
    trash_sample: int | None = None,
    drop_sample_in_tip: int | None = None,
    spare_ul: float = 0,
    buffer_in_plate_ul: float | None = None,
) -> Trace:
    loads = {tube("A1"): ("PCR master mix", mix_declared)}
    loads.update({tube(name): (f"DNA sample {i}", 30.0) for i, name in enumerate(TUBES, 1)})
    if buffer_in_plate_ul is not None:  # the first destination already holds buffer
        loads[plate(dests[0])] = ("buffer", buffer_in_plate_ul)
    b = TraceBuilder(loads)
    b.pick_up(tip("A1"))
    for dest in dests:
        b.aspirate(tip("A1"), tube("A1"), 20)
        b.dispense(tip("A1"), plate(dest), 20, height=ABOVE)
    b.drop(tip("A1"))
    for n, (source, dest) in enumerate(zip(sample_order, dests, strict=True)):
        t = tip(f"A{n + 2}")
        b.pick_up(t)
        b.aspirate(t, tube(TUBES[source]), sample_ul + spare_ul)
        if n == trash_sample:
            b.blow_out(t, tube("D6"))  # stands in for a waste well
        elif n != drop_sample_in_tip:
            b.dispense(t, plate(dest), sample_ul)
        b.drop(t)
    return Trace(b.deck, b.events)


def pcr_map(**changes: Any) -> PlateMap:
    row: dict[str, Any] = {
        "id": "pcr4",
        "request": "20 ul master mix + 5 ul of each of 4 samples",
        "liquids": [
            {"name": "master_mix", "role": "reagent", "bind": "name", "pattern": "(?i)master mix"},
            {"name": "sample_{i}", "role": "sample", "bind": "indexed",
             "pattern": r"(?i)sample\s*(\d+)", "count": 4, "index": "number"},
        ],
        "destination": {"select": "auto"},
        "variants": [
            {"name": "pinned", "why": "", "groups": [],
             "pinned": {d: {"master_mix": 20, f"sample_{i}": 5} for i, d in enumerate(DESTS, 1)}}
        ],
    }  # fmt: skip
    row.update(changes)
    return platemap_from_dict(row)


def free_map(order_hint: str | None = "index") -> PlateMap:
    members = [{"master_mix": 20, f"sample_{i}": 5} for i in range(1, 5)]
    group = {"name": "reactions", "members": members, "order_hint": order_hint}
    return pcr_map(variants=[{"name": "free", "why": "", "pinned": {}, "groups": [group]}])
