"""MIX-BEFORE-DRAW: liquid was added to a different liquid, then drawn out with no mixing between.

In words. A well already holds liquid. The protocol dispenses a *different* liquid into it, and
later draws liquid out of that well, and nowhere in between does it mix the well. Two liquids
layered in a small well do not mix on their own, so what the tip draws is not at the
concentration the author calculated. In a dilution series every later step inherits the error.

Mixing means a `mix` (also `mix_after` / `mix_before` of a transfer), or by hand: an aspirate
from the well followed straight away by a dispense back into it with the same tip.

It does not fire when the well was empty, when the same liquid is topped up, when the draw
takes (nearly) all of the well, or when everything drawn goes to the trash: then the
concentration of what was drawn does not matter.
"""

from __future__ import annotations

from dataclasses import dataclass

from provette.model import Trace, WellKey
from provette.rules import sources
from provette.rules.common import (
    Facts,
    Move,
    facts_of,
    is_real,
    listing,
    stack_key,
    times,
    well_listing,
)
from provette.rules.finding import Downstream, Finding
from provette.rules.rule import Rule
from provette.state import Run, WellState

RULE_ID = "MIX-BEFORE-DRAW"
TITLE = "Liquid drawn from a well that was not mixed after an addition"

WHOLE_WELL = 0.9  # a draw of this share of the well takes everything: layering cannot matter
SAME_SHARE = 0.01  # two compositions are the same if every share agrees this closely


@dataclass(frozen=True)
class _UnmixedDraw:
    added_at: int  # the dispense that layered a different liquid into the well
    drawn_at: int
    well: WellKey
    recipients: tuple[WellKey, ...]


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    groups: dict[tuple[str, ...], list[_UnmixedDraw]] = {}
    for draw in _unmixed_draws(facts):
        groups.setdefault(stack_key(facts.event(draw.added_at)), []).append(draw)

    findings = []
    for group in groups.values():
        added = facts.event(group[0].added_at)
        wells = facts.refs(d.well for d in group)
        drawn = {d.well for d in group}
        reached = facts.refs(w for d in group for w in d.recipients if w not in drawn)
        draw_lines = sorted({facts.event(d.drawn_at).line or 0 for d in group})
        count = len({d.added_at for d in group})
        explanation = (
            f"At line {added.line} liquid was added to {well_listing(wells)}, which already "
            f"held a different liquid{'' if count == 1 else f' (this line did it {times(count)})'}"
            f". At {listing([f'line {n}' for n in draw_lines])} liquid was drawn out of "
            f"{'it' if len(wells) == 1 else 'them'} again, and the well was never mixed in "
            "between. Two liquids layered in a small well do not mix on their own, so what the "
            "tip drew is not at the concentration you calculated. In a dilution series every "
            "later step inherits the error."
        )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity="warning",
                certain=True,
                roles_basis="none",
                title=(
                    "Liquid drawn from "
                    + (well_listing(wells) if len(wells) == 1 else f"{len(wells)} wells")
                    + f" before it was mixed: added at line {added.line}, drawn at "
                    + listing([f"line {n}" for n in draw_lines])
                ),
                explanation=explanation,
                fix=(
                    f"Mix the well after the addition at line {added.line}: `mix_after=(5, volume)`"
                    " in a transfer, or `pipette.mix(5, volume, well)`. Integra suggests about "
                    "5 cycles at about 80% of the volume in the well."
                ),
                line=added.line,
                stack=tuple(added.stack),
                occurrences=facts.occurrences(d.added_at for d in group),
                wells=wells,
                downstream=Downstream(len(reached), reached),
                sources=RULE.sources,
            )
        )
    return findings


def _unmixed_draws(facts: Facts) -> list[_UnmixedDraw]:
    run = facts.run
    unmixed: dict[WellKey, int] = {}  # well -> the addition it has not been mixed since
    found = []
    for move in facts.moves:
        before = run.well_before(move.well, move.event_index)
        if move in facts.strokes:
            unmixed.pop(move.well, None)
        elif not move.is_aspirate:
            if not _holds_liquid(before):
                unmixed.pop(move.well, None)
            elif not _same_liquid(facts, before, run.well_before(move.well, move.event_index + 1)):
                unmixed[move.well] = move.event_index
        elif move.well in unmixed:
            went = facts.recipients.get(move, ())
            takes_all = (
                before.volume_ul is not None
                and _drawn_ul(facts, move) >= WHOLE_WELL * before.volume_ul
            )
            if takes_all or (went and all(_is_trash(w) for w in went)):
                continue
            kept = tuple(w for w in went if not _is_trash(w))
            found.append(_UnmixedDraw(unmixed[move.well], move.event_index, move.well, kept))
    return found


def _holds_liquid(state: WellState) -> bool:
    return state.volume_ul is None or state.volume_ul > 0


def _drawn_ul(facts: Facts, move: Move) -> float:
    contacts = facts.run.steps[move.event_index].contacts
    return sum(c.liquid_ul for c in contacts if c.well == move.well)


def _is_trash(well: WellKey) -> bool:
    return "trash" in well.labware_id.lower()


def _shares(facts: Facts, amounts: dict[WellKey, float | None]) -> dict[str, float | None]:
    """Liquid -> amount, with liquids declared under one name counted as one liquid."""
    shares: dict[str, float | None] = {}
    for atom, amount in amounts.items():
        name = facts.liquid_name(atom) or str(atom)
        held = shares.get(name, 0.0)
        shares[name] = None if held is None or amount is None else held + amount
    return shares


def _same_liquid(facts: Facts, before: WellState, after: WellState) -> bool:
    """Was what came in the same liquid as what was there? Unknown amounts count as the same."""
    was = _shares(facts, {a: p.volume_ul for a, p in before.atoms.items() if is_real(p)})
    came: dict[WellKey, float | None] = {}
    for atom, presence in after.atoms.items():
        old = before.atoms.get(atom)
        had = old.volume_ul if old is not None else 0.0
        if had is None:
            continue  # an unknown amount was there already: no telling whether more came
        if presence.volume_ul is None:
            came[atom] = None  # it came, in an unknown amount
        elif presence.volume_ul - had > 1e-9:
            came[atom] = presence.volume_ul - had
    new = _shares(facts, came)
    if not new:
        return True
    if set(new) - set(was):
        return False
    if len(was) == 1:
        return True
    if set(new) != set(was):
        return False
    known_was = [v for v in was.values() if v is not None]
    known_new = [v for v in new.values() if v is not None]
    if len(known_was) != len(was) or len(known_new) != len(new):
        return True
    total_was, total_new = sum(known_was), sum(known_new)
    return all(
        abs((was[k] or 0.0) / total_was - (new[k] or 0.0) / total_new) <= SAME_SHARE for k in was
    )


RULE = Rule(
    rule_id=RULE_ID,
    family=3,
    tier="structural",
    title=TITLE,
    description=(
        "A well that holds liquid receives a different liquid, and liquid is later drawn out of "
        "it with no mixing of that well in between. Warning."
    ),
    sources=(sources.INTEGRA_SERIAL_DILUTION, sources.SVEC_2015),
    check=check,
)
