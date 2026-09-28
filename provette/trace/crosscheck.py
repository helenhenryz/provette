"""The cross-check of D-09 (DECISIONS.md): the broker trace and the analysis must tell one story."""

from __future__ import annotations

from provette.model import Event, Trace
from provette.trace.analyze import LiquidOp

COMPARED = ("pick_up_tip", "aspirate", "dispense", "blow_out", "drop_tip")
VOLUME_TOLERANCE_UL = 1e-6


def cross_check(trace: Trace, ops: list[LiquidOp]) -> list[str]:
    """Every way the two sources disagree, in words. An empty list means they agree.

    Compared, in order: the op, the labware (load name and first slot), the well and the volume
    of every pick_up_tip, aspirate, dispense, blow_out and drop_tip.

    * An 8-channel event is compared on its first channel's well, which is the well the analysis
      names. When fewer tips than channels are in play (a partly empty rack column, a pipette
      hanging over the edge of a plate) the first target is no longer that well, so only the
      labware is compared.
    * An air gap is an `aspirate` on both sides: the analysis reports it in place, and
      `reduce_analysis` gives it the well of the move before it, which is the well the trace
      names.
    * An aspirate or dispense of 0 uL (`dispense(pipette.current_volume)` with an empty tip,
      or any dispense from an empty tip) moves nothing, but the tip does go into the well, so
      the trace keeps the event. The analysis has either a plain move, which is not a liquid
      operation (below API 2.14, when 0 was asked for), or the same step (as 0 uL from 2.14;
      below 2.14 with whatever volume was asked for). Such an event is matched with the next
      analysis operation if that is the same step, and otherwise passed over.
    * A dispense of more than the tip holds dispenses what it holds (up to API 2.16; later it
      is an error). The trace records what the tip held. Below API 2.14 the analysis is built
      from the broker's announcement and repeats the volume asked for, so there a larger
      analysis volume on a dispense is not a disagreement. From 2.14 both say what the tip held.
    * The analysis gives a volume only for aspirates and dispenses, so only those compare it.
    """
    channels: dict[str | None, int] = {p.mount: p.channels for p in trace.deck.pipettes}
    major, _, minor = trace.deck.api_level.partition(".")
    old_engine = (int(major), int(minor)) < (2, 14)
    events = [e for e in trace.events if e.op in COMPARED]
    problems = []
    position = 0  # in `ops`
    for number, event in enumerate(events):
        op = ops[position] if position < len(ops) else None
        if event.volume_ul == 0:
            # The tip went into the well and moved nothing. The analysis may have the step (as
            # 0 uL, or on the old engine with the volume asked for) or only a plain move. It
            # has the step if the operation fits this event and not the next event that moves
            # liquid or a tip.
            following = next((e for e in events[number + 1 :] if e.volume_ul != 0), None)

            def fits(candidate: Event | None, op: LiquidOp | None = op) -> bool:
                if candidate is None or op is None:
                    return False
                return not _differences(candidate, op, channels.get(candidate.mount, 1), True)

            if fits(event) and (op is not None and op.volume_ul == 0 or not fits(following)):
                position += 1
            continue
        if op is None:
            problems.append(f"event {event.index} (line {event.line}) is not in the analysis")
            continue
        differences = _differences(event, op, channels.get(event.mount, 1), old_engine)
        if differences:
            where = f"liquid operation {position} (event {event.index}, line {event.line})"
            problems.append(f"{where}: " + "; ".join(differences))
        position += 1
    if position < len(ops):
        problems.append(f"the analysis has {len(ops) - position} liquid operations more")
    return problems


def _differences(event: Event, op: LiquidOp, channels: int, old_engine: bool) -> list[str]:
    found = []
    if event.op != op.op:
        return [f"trace says {event.op}, analysis says {op.op}"]
    if event.targets:
        first = event.targets[0].well
        slot, _, load_name = first.labware_id.partition(":")
        if load_name != op.labware_load_name:
            found.append(f"trace labware {load_name}, analysis {op.labware_load_name}")
        if op.slot is not None and slot != op.slot:
            found.append(f"trace slot {slot}, analysis slot {op.slot}")
        whole = len(event.targets) == channels
        if op.well is not None and whole and first.well != op.well:
            found.append(f"trace well {first.well}, analysis well {op.well}")
    elif op.labware_load_name is not None:
        found.append(f"trace names no well, analysis names {op.labware_load_name}[{op.well}]")
    if event.op in ("aspirate", "dispense"):
        ours, theirs = event.volume_ul, op.volume_ul
        if ours is None or theirs is None:
            found.append(f"trace volume {ours}, analysis volume {theirs}")
        elif old_engine and event.op == "dispense" and theirs > ours:
            pass  # the analysis repeats the volume asked for; the trace has what the tip held
        elif abs(ours - theirs) > VOLUME_TOLERANCE_UL:
            found.append(f"trace volume {ours}, analysis volume {theirs}")
    return found
