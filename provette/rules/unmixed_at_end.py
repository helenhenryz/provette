"""UNMIXED-AT-END: a well was never mixed after its last addition, and the run ended.

In words. When a small volume is dropped into a larger one, the two sit in layers: 2 ul of
template under 18 ul of master mix, 5 ul of loading dye on 15 ul of protein, 3 ul of DNA under
47 ul of water. Nothing in a small well mixes them on its own. `MIX-BEFORE-DRAW` catches the
case where the protocol draws from the layered well; this rule catches the case where the
protocol simply ends. A PCR plate is usually vortexed and spun before cycling, so a layered
well that holds a PCR liquid (master mix, polymerase, SYBR: `MIX_WORDS`, by the declared name
or description) is a note. A normalisation, a pool, a Bradford well or a gel sample has nothing
after it: when the last addition there is a sample (a DNA into water, a library into a pool),
nothing else will ever mix it, and a normalisation that is not mixed is not normalised: a
warning. Anything else is a note.

One finding per root line: at the end of the run, a well that holds two or more different
liquids in bulk, whose last addition of a liquid it did not yet hold was a dispense of less than
30% of what the well held after it, with no mixing stroke in that well after it
(`facts.strokes`: `mix`, `mix_after`, or an aspirate-and-return with the same tip) and no draw
from the well after it. The finding lists the wells and says what was added on what. Always
certain.

It does not fire on a well drawn from after the addition (`MIX-BEFORE-DRAW`'s); on an addition
of 30% or more of the well (it mixes on entry: the same reasoning as `MIX-BEFORE-DRAW`'s
whole-well threshold); on a top-up, which is more of a liquid the well already holds, whether
from the same tube or, as in a waste tube fed by every step of a dilution series, the same
liquids in another proportion; on a well of unknown volume; on a well whose last addition was
followed by a mixing stroke; on trash and waste labware; on a sink, a reservoir channel the
robot only ever pours into and never draws from, whatever it is called (`WELL-CAPACITY`'s
exclusion, without its tubes: a pool is a tube only ever poured into, and the catalogue names
pools as a warning). A `blow_out` into the well is neither an addition nor a mix.

The catalogue also raises the severity by the plate map's technique (a normalisation, a protein
gel, a Bradford, a pool). The map does not carry a technique yet, so that clause is not built:
the well's contents and the role of the last addition decide.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace

from provette.model import Trace, WellKey
from provette.rules import sources
from provette.rules.common import (
    Facts,
    facts_of,
    is_real,
    listing,
    place,
    stack_key,
    times,
    well_listing,
)
from provette.rules.finding import Downstream, Finding, RolesBasis, Severity
from provette.rules.rule import Rule
from provette.state import Presence, Run, WellState

RULE_ID = "UNMIXED-AT-END"
TITLE = "A well was never mixed after its last addition"

MIXES_ON_ENTRY = 0.3  # an addition of this share of the well, or more, mixes as it lands
GOOD_SHARE = 0.8  # what the fix suggests: Integra's "about 80% of the volume"
GOOD_STROKES = 5
WASTE_WORDS = ("waste", "trash")
SINK_WORDS = ("reservoir",)  # not "tube": a pool is a tube only ever poured into
# A PCR liquid, by name or description; moves to roles.py when the `ntc` branch merges.
MIX_WORDS = re.compile(r"\bmaster ?mix\b|\bmix\b|\bsybr\b|\btaq\b|\bpolymerase\b|\bqpcr\b|\bpcr\b")


@dataclass(frozen=True)
class _Layered:
    """A well the run left layered: the last addition of a new liquid, and its share."""

    added_at: int  # the dispense that layered a new liquid into the well
    well: WellKey
    added: tuple[WellKey, ...]  # the liquids that dispense brought which the well did not hold
    held: tuple[WellKey, ...]  # what the well held in bulk before it
    share: float  # of the well's volume after the dispense
    final_ul: float  # what the well holds at the end of the run


def check(trace: Trace, run: Run) -> list[Finding]:
    facts = facts_of(trace, run)
    groups: dict[tuple[str, ...], list[_Layered]] = {}
    for layered in _left_layered(facts):
        groups.setdefault(stack_key(facts.event(layered.added_at)), []).append(layered)

    findings = []
    for group in groups.values():
        added = facts.event(group[0].added_at)
        wells = facts.refs(w.well for w in group)
        count = len({w.added_at for w in group})
        added_names = _names(facts, (a for w in group for a in w.added))
        base_names = _names(facts, (a for w in group for a in w.held))
        severity, basis, pcr = _severity(facts, group)
        shares = _range(round(100 * w.share) for w in group)
        good = _range(round(GOOD_SHARE * w.final_ul) for w in group)
        explanation = (
            f"At line {added.line} the robot added {listing(added_names)} to "
            f"{well_listing(wells)}, which already held {listing(base_names)}"
            f"{'' if count == 1 else f' (this line did it {times(count)})'}. The addition was "
            f"{shares}% of the well, nothing mixed the well afterwards, and the run ended with "
            f"{'it' if len(wells) == 1 else 'them'} that way. Two liquids layered in a small "
            "well do not mix on their own, so what the well holds is not at the concentration "
            "you calculated. " + _why(severity, pcr)
        )
        findings.append(
            Finding(
                rule_id=RULE_ID,
                family=RULE.family,
                tier=RULE.tier,
                severity=severity,
                certain=True,
                roles_basis=basis,
                title=(
                    (
                        (lambda s: s[0].upper() + s[1:])(well_listing(wells))
                        if len(wells) == 1
                        else f"{len(wells)} wells"
                    )
                    + f" never mixed after {listing(added_names)} went in ({shares}% of the well)"
                ),
                explanation=explanation,
                fix=(
                    f"Mix {well_listing(wells)} after line {added.line}: "
                    f"`mix_after=({GOOD_STROKES}, {good})` on the transfer, or "
                    f"`pipette.mix({GOOD_STROKES}, {good}, well)`, with the volume about "
                    f"{round(100 * GOOD_SHARE)}% of what the well holds."
                ),
                line=added.line,
                stack=tuple(added.stack),
                occurrences=facts.occurrences(w.added_at for w in group),
                wells=wells,
                downstream=Downstream(0, ()),
                sources=RULE.sources,
            )
        )
    return findings


def _left_layered(facts: Facts) -> list[_Layered]:
    """Every well the run ends with layered: the last addition of a new liquid stands, with no
    mixing stroke and no draw from the well after it."""
    run = facts.run
    pending: dict[WellKey, _Layered] = {}
    for move in facts.moves:
        if facts.event(move.event_index).op == "blow_out":
            continue  # neither an addition nor a mix
        if move in facts.strokes or move.is_aspirate:
            pending.pop(move.well, None)  # mixed, or drawn from (MIX-BEFORE-DRAW's)
            continue
        before = run.well_before(move.well, move.event_index)
        after = run.well_before(move.well, move.event_index + 1)
        if before.volume_ul is None or after.volume_ul is None or after.volume_ul <= 0:
            pending.pop(move.well, None)  # unknown volume: the share cannot be known
            continue
        if before.volume_ul <= 0:
            pending.pop(move.well, None)  # the well was empty: nothing to layer on
            continue
        share = move.liquid_ul / after.volume_ul
        if share >= MIXES_ON_ENTRY:
            pending.pop(move.well, None)  # a large addition mixes as it lands
            continue
        held = tuple(a for a, p in before.atoms.items() if _in_bulk(p))
        new = _new_liquids(facts, held, after)
        if new:
            pending[move.well] = _Layered(move.event_index, move.well, new, held, share, 0.0)
        # a small top-up of liquids the well already holds leaves the layers as they were
    layered = []
    for well, found in pending.items():
        final = run.wells[well]
        if final.volume_ul is None or final.volume_ul <= 0 or _is_sink(facts, well):
            continue
        if len(_names(facts, (a for a, p in final.atoms.items() if _in_bulk(p)))) < 2:
            continue
        layered.append(replace(found, final_ul=final.volume_ul))
    return sorted(layered, key=lambda w: w.added_at)


def _new_liquids(facts: Facts, held: tuple[WellKey, ...], after: WellState) -> tuple[WellKey, ...]:
    """The liquids now in bulk in the well that it did not hold before, by declared name: more
    of the same liquid, from the same tube or another, is a top-up and not a new layer."""
    names = set(_names(facts, held))
    return tuple(
        atom
        for atom, presence in after.atoms.items()
        if _in_bulk(presence) and atom not in held and _names(facts, (atom,))[0] not in names
    )


def _in_bulk(presence: Presence | None) -> bool:
    """Real liquid put there by the protocol, as opposed to the film a tip left behind."""
    return is_real(presence) and presence is not None and presence.mode == "bulk"


def _names(facts: Facts, atoms: Iterable[WellKey]) -> list[str]:
    """The declared names of these liquids, each once, in the order first met; an undeclared
    liquid is named by the well it came from."""
    names: list[str] = []
    for atom in atoms:
        name = facts.liquid_name(atom) or f"the liquid from {place(facts.ref(atom))}"
        if name not in names:
            names.append(name)
    return names


def _severity(facts: Facts, group: list[_Layered]) -> tuple[Severity, RolesBasis, bool]:
    """A well holding a PCR liquid is a note: the plate is usually vortexed and spun before
    cycling. Otherwise a warning when the liquid added last is a sample, because nothing else
    will mix it, and a note if not. The worst well of the group decides; the basis says whether
    a declared name decided it; the flag says whether every well is a PCR well."""
    worst: Severity = "note"
    known = False
    pcr_wells = 0
    for found in group:
        final = facts.run.wells[found.well]
        if any(_pcr_liquid(facts, a) for a, p in final.atoms.items() if _in_bulk(p)):
            pcr_wells += 1
            known = True
            continue
        roles = {facts.role(atom) for atom in found.added}
        known = known or bool(roles - {None})
        if "sample" in roles:
            worst = "warning"
    return worst, "declared" if known else "none", pcr_wells == len(group)


def _pcr_liquid(facts: Facts, atom: WellKey) -> bool:
    origin = facts.run.origins.get(atom)
    if origin is None:
        return False
    return any(
        MIX_WORDS.search(text.lower())
        for load in origin.loads
        for text in (load.liquid_name, load.description)
        if text
    )


def _why(severity: Severity, pcr: bool) -> str:
    if pcr:
        return (
            "A PCR plate is usually vortexed and spun down before cycling; if this one will not "
            "be, mix it."
        )
    if severity == "warning":
        return (
            "The liquid added last is a sample, so nothing else in the workflow will mix it: a "
            "normalisation or a pool left like this is not what it says it is."
        )
    return (
        "If the plate is vortexed and spun down before it is used, nothing is wrong; if it goes "
        "straight to the instrument, the wells are not what the protocol says they are."
    )


def _is_sink(facts: Facts, well: WellKey) -> bool:
    """Waste or trash by name; or a reservoir channel the robot only pours into and never draws
    from, whatever it is called. A tube never drawn from stays in scope: a pool is one."""
    ref = facts.ref(well)
    text = f"{ref.labware_id} {ref.labware}".lower()
    if any(word in text for word in WASTE_WORDS):
        return True
    return any(word in text for word in SINK_WORDS) and not any(
        move.is_aspirate and move.well == well for move in facts.moves
    )


def _range(values: Iterable[int]) -> str:
    """ "20" when every value agrees; "4 to 20" otherwise."""
    seen = sorted(set(values))
    return f"{seen[0]}" if len(seen) == 1 else f"{seen[0]} to {seen[-1]}"


RULE = Rule(
    rule_id=RULE_ID,
    family=3,
    tier="structural",
    title=TITLE,
    description=(
        "At the end of the run a well holds two or more different liquids, the last one added "
        "was under 30% of the well, and nothing mixed the well or drew from it afterwards. "
        "Note when the well holds a PCR liquid (the plate is vortexed before cycling); "
        "otherwise warning when the liquid added last is a sample, note if not. Silent on "
        "waste and trash, and on a reservoir channel only ever poured into."
    ),
    sources=(
        sources.ARTEL_SOURCES_OF_ERROR,
        sources.ILLUMINA_NORMALISING_LIBRARIES,
        sources.THERMO_POWERTRACK,
        sources.INTEGRA_SERIAL_DILUTION,
    ),
    check=check,
)
