"""A digest of everything a `Run` says, to prove that a change to the replay changed no result.

Order counts wherever order is data: steps, contacts and arrivals within a step, the atoms of a
well, the residue and layers of a tip. `well_before` is sampled at forty points of the run.
"""

from __future__ import annotations

import hashlib

from provette.model import Trace
from provette.state import Run, WellState


def _well(state: WellState) -> tuple[object, ...]:
    atoms = list(state.atoms.items())
    return (state.well, state.volume_ul, state.min_volume_ul, state.received_liquid, atoms)


def digest(run: Run, trace: Trace) -> str:
    sha = hashlib.sha256()

    def add(item: object) -> None:
        sha.update(repr(item).encode() + b"\n")

    for step in run.steps:
        add(step)
    for key in sorted(run.wells):
        add(_well(run.wells[key]))
    for key in sorted(run.origins):
        add(run.origins[key])
    for anomaly in run.anomalies:
        add(anomaly)
    for key in sorted(run.tips):
        tip = run.tips[key]
        layers = [
            (x.volume_ul, None if x.atoms is None else list(x.atoms.items())) for x in tip.layers
        ]
        add((tip.tip, tip.status, tip.picked_up_event, layers, list(tip.residue.items())))
    add(run.end_s)
    count = len(trace.events)
    for i in range(0, count + 1, max(1, count // 40)):
        for event in trace.events[max(0, i - 2) : i + 2]:
            for target in event.targets:
                if target.well in run.wells:
                    add((i, _well(run.well_before(target.well, i))))
    for atom in sorted(run.origins)[:20]:
        add(run.downstream(atom))
    return sha.hexdigest()
