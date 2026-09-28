"""NO-NEGATIVE-CONTROL: a PCR plate with no well that has everything except the template.

In words. A PCR or qPCR plate needs one well with everything except the template: if that well
lights up, a reagent is contaminated or the primers pair with each other, and every other
well's signal is in doubt. MIQE lists the no-template control as essential on every plate, and
every master-mix manual says the same. A standard curve needs a blank, the diluent in place of
the sample; an RT-qPCR plate needs a well without the reverse transcriptase, so that signal
from leftover genomic DNA can be told from the cDNA. The requests in eval/agent never ask for
these, so the models never add them: 10 of 10 PCR and qPCR drafts had no NTC. This is advice to
the writer and to the person approving the plate map, not a defect against the map, so every
finding is a note.

The plate is a PCR plate when a declared reagent whose name or description has a mix word
(master mix, mastermix, mix, SYBR, Taq, polymerase, qPCR, PCR: `roles.is_mix_word`) ends in
bulk in at least four destination wells of one labware that also hold a sample-role liquid in
bulk. Those are the reaction wells. Three notes, one of each per plate:

* `no_ntc`: no destination well on the plate ends holding the mix in bulk and no sample-role
  liquid as real liquid. A well of mix and water is an NTC; a well of mix alone is one too. A
  film of sample left by a tip does not unmake an NTC: that is CONTAM-WELL's finding.
* `no_blank`: one sample-role liquid (one declared tube of it) reaches at least four wells at
  concentrations that fall by a constant factor, within 5%, from level to level; or reaches
  wells at three or more distinct concentrations, diluted with a carrier; and no well on the
  plate holds a carrier with no sample. The blank may be a well the robot filled or a well of
  diluent that was there from the start, and it may hold a reagent too (the Bradford reagent
  goes into the blank as well). Concentration is the liquid's amount over the well's volume,
  so a series built in tubes and then plated is still a series.
* `no_rt_control`: a reagent (or a liquid the word lists cannot place) whose name or
  description says RT, RTase or reverse transcriptase (`roles.is_rt_word`) reaches the reaction
  wells, and no well on the plate holds the same samples and reagents without it. Silent when
  the RT word is only in the mix's own name (a one-step mix): the control then needs a
  different mix, and the rule cannot see which.

Each finding is anchored on the line that first puts the mix (or, for the blank, the sample)
into that plate, lists the reaction wells, and is certain, with `roles_basis` "declared".

What it does not fire on: a protocol that declares no liquids; a plate with fewer than four
reaction wells; a plate where the mix is handed out to the NTC well first and the samples come
later (the NTC exists); a normalisation or a pooling (no mix-role liquid); pre-made standards
that arrive in tubes at different concentrations, because a declaration carries no
concentration, so the state sees one liquid per tube at one level each. The plate map's
"controls" field (none, or the wells the controls are in) does not exist yet; when it does, a
map that says so silences the rule, and until then the rule cannot be told a control is not
wanted.
"""

from __future__ import annotations

from dataclasses import dataclass

from provette.model import Trace, WellKey
from provette.rules import sources
from provette.rules.common import (
    Facts,
    facts_of,
    is_real,
    listing,
    natural,
    well_count,
    well_listing,
)
from provette.rules.finding import Downstream, Finding, WellRef
from provette.rules.roles import Role, is_mix_word, is_rt_word
from provette.rules.rule import Rule
from provette.state import Presence, Run, WellState

RULE_ID = "NO-NEGATIVE-CONTROL"
MIN_REACTION_WELLS = 4  # fewer is not a plate worth a control
MIN_SERIES_LEVELS = 4  # a series falling by one constant factor
MIN_LEVELS_WITH_CARRIER = 3  # or this many distinct concentrations, diluted with a carrier
SERIES_TOLERANCE = 0.05  # levels, and the factor between them, are the same within this


@dataclass(frozen=True)
class _Plate:
    """One labware the robot dispensed into, with the wells that received liquid."""

    labware_id: str
    wells: tuple[WellState, ...]  # the destination wells, in plate order
    everything: tuple[WellState, ...]  # every well on it, stocks included


class _Kinds:
    """What each declared liquid is, by its declared name and description, worked out once."""

    def __init__(self, facts: Facts) -> None:
        self.facts = facts
        self.mix: set[WellKey] = set()
        self.rt: set[WellKey] = set()
        self.by_role: dict[WellKey, Role | None] = {}
        for atom, origin in facts.run.origins.items():
            if not origin.loads:
                continue
            load = origin.loads[0]
            role = facts.role(atom)
            self.by_role[atom] = role
            if role == "reagent" and is_mix_word(load.liquid_name, load.description):
                self.mix.add(atom)
            if role in ("reagent", None) and is_rt_word(load.liquid_name, load.description):
                self.rt.add(atom)

    def role(self, atom: WellKey) -> Role | None:
        return self.by_role.get(atom)

    def name(self, atom: WellKey) -> str:
        return self.facts.liquid_name(atom) or "the liquid"


def _bulk(state: WellState) -> dict[WellKey, Presence]:
    """The liquids really in the well at the end: put there as liquid, not left as a film."""
    return {a: p for a, p in state.atoms.items() if _real_bulk(p)}


def check(trace: Trace, run: Run) -> list[Finding]:
    if not trace.deck.liquid_loads:
        return []  # nothing is declared, so no liquid is a mix or a sample
    facts = facts_of(trace, run)
    kinds = _Kinds(facts)
    if not any(kinds.role(a) == "sample" for a in kinds.by_role):
        return []
    findings: list[Finding] = []
    for plate in _plates(run):
        reaction = _reaction_wells(kinds, plate)
        if len(reaction) >= MIN_REACTION_WELLS:
            findings += _no_ntc(facts, kinds, plate, reaction)
            findings += _no_rt_control(facts, kinds, plate, reaction)
        findings += _no_blank(facts, kinds, plate)
    return findings


def _plates(run: Run) -> list[_Plate]:
    by_labware: dict[str, list[WellState]] = {}
    for well in sorted(run.wells, key=natural):
        by_labware.setdefault(well.labware_id, []).append(run.wells[well])
    return [
        _Plate(labware_id, tuple(s for s in states if s.received_liquid), tuple(states))
        for labware_id, states in sorted(by_labware.items())
        if any(s.received_liquid for s in states)
    ]


def _reaction_wells(kinds: _Kinds, plate: _Plate) -> list[WellState]:
    """The wells that end with a mix and a sample, both as liquid."""
    reaction = []
    for state in plate.wells:
        bulk = _bulk(state)
        if any(a in kinds.mix for a in bulk) and any(kinds.role(a) == "sample" for a in bulk):
            reaction.append(state)
    return reaction


def _first_bulk_event(run: Run, atoms: set[WellKey], wells: list[WellState]) -> list[int]:
    """The event that first put any of `atoms` into each of `wells` as real liquid, in order.

    Read off the well's history rather than the arrivals: an arrival is logged again only when
    it improves from carry-over to bulk or from uncertain to certain, not when a trace carried
    inside another liquid (0.0) becomes a real dispense, so a mix that first reached the well
    as a trace has no arrival for the dispense that matters.
    """
    events: set[int] = set()
    for state in wells:
        for event_index, after in run.history.get(state.well, []):
            if any(_real_bulk(after.atoms.get(atom)) for atom in atoms):
                events.add(event_index)
                break
    return sorted(events)


def _real_bulk(presence: Presence | None) -> bool:
    return presence is not None and presence.mode == "bulk" and is_real(presence)


# -- no_ntc --------------------------------------------------------------------------------------


def _no_ntc(facts: Facts, kinds: _Kinds, plate: _Plate, reaction: list[WellState]) -> list[Finding]:
    mixes = {a for state in reaction for a in _bulk(state) if a in kinds.mix}
    for state in plate.wells:
        bulk = _bulk(state)
        if any(a in mixes for a in bulk) and not any(kinds.role(a) == "sample" for a in bulk):
            return []  # the NTC exists: mix with water, or mix alone
    events = _first_bulk_event(facts.run, mixes, reaction)
    if not events:
        return []
    first = facts.event(events[0])
    wells = facts.refs(s.well for s in reaction)
    mix_names = sorted({kinds.name(a) for a in mixes})
    mix_ul, sample_ul = _doses(kinds, reaction[0], mixes)
    mix_words = listing(mix_names)
    return [
        _finding(
            facts,
            f"No no-template control: {well_count(wells)} of {mix_words} with a sample",
            (
                f"At line {first.line} the robot starts putting {mix_words} into "
                f"{_plate_words(wells)}, and {well_count(wells)} end holding it together with a "
                "sample. No well on this plate holds the mix without a sample, so there is no "
                "no-template control. If a reagent is contaminated, or the primers pair with "
                "each other, every well gives a signal and nothing on the plate can tell that "
                "from a real one."
            ),
            (
                f"Add one well (three for qPCR) with {mix_ul} of {mix_words} and {sample_ul} "
                "of water in place of the template, and tell the plate map where it is."
            ),
            events,
            wells,
        )
    ]


def _doses(kinds: _Kinds, state: WellState, mixes: set[WellKey]) -> tuple[str, str]:
    """The mix and the sample amounts in one reaction well, as words: "15 ul", "5 ul"."""
    bulk = _bulk(state)
    mix = [p.volume_ul for a, p in bulk.items() if a in mixes]
    sample = [p.volume_ul for a, p in bulk.items() if kinds.role(a) == "sample"]

    def words(amounts: list[float | None]) -> str:
        if not amounts or any(v is None for v in amounts):
            return "the same amount"
        return f"{sum(v for v in amounts if v is not None):g} ul"

    return words(mix), words(sample)


# -- no_blank ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Series:
    atom: WellKey
    wells: tuple[WellState, ...]
    levels: int
    factor: float | None  # the constant factor, when there is one


def _no_blank(facts: Facts, kinds: _Kinds, plate: _Plate) -> list[Finding]:
    series = _series_on(kinds, plate)
    if series is None:
        return []
    for state in plate.everything:
        bulk = _bulk(state)
        roles = {kinds.role(a) for a in bulk}
        if "carrier" in roles and "sample" not in roles:
            return []  # the blank exists: diluent with no sample, whatever else is in it
    events = _first_bulk_event(facts.run, {series.atom}, list(series.wells))
    if not events:
        return []
    first = facts.event(events[0])
    wells = facts.refs(s.well for s in series.wells)
    sample = kinds.name(series.atom)
    carriers = sorted(
        {kinds.name(a) for s in series.wells for a in _bulk(s) if kinds.role(a) == "carrier"}
    )
    diluent = listing(carriers) if carriers else "the diluent"
    steps = (
        f"each level about {series.factor:g} times weaker than the one before"
        if series.factor is not None
        else f"diluted with {diluent}"
    )
    return [
        _finding(
            facts,
            f"No blank on a dilution series: {well_count(wells)} of {sample}",
            (
                f"At line {first.line} the robot starts a dilution series of {sample} in "
                f"{_plate_words(wells)}: {well_count(wells)} at {series.levels} concentrations, "
                f"{steps}. No well on this plate holds {diluent} with no sample, so there is "
                "no blank: the curve has no zero to read against, and a signal from the "
                "diluent or the plastic cannot be told from the lowest point."
            ),
            f"Add a well of {diluent} alone, and tell the plate map where it is.",
            events,
            wells,
        )
    ]


def _series_on(kinds: _Kinds, plate: _Plate) -> _Series | None:
    """The first sample-role liquid that forms a dilution series on the plate, if any."""
    found: dict[WellKey, list[tuple[float, WellState]]] = {}
    for state in plate.wells:
        if state.volume_ul is None or state.volume_ul <= 0:
            continue
        for atom, presence in _bulk(state).items():
            if kinds.role(atom) != "sample" or presence.volume_ul is None:
                continue
            found.setdefault(atom, []).append((presence.volume_ul / state.volume_ul, state))
    for atom, points in sorted(found.items(), key=lambda item: natural(item[0])):
        if len(points) < MIN_REACTION_WELLS:
            continue
        levels = _levels(points)
        factor = _constant_factor([top for top, _ in levels])
        with_carrier = all(
            any(kinds.role(a) == "carrier" for a in _bulk(state)) for _, state in points
        )
        if (len(levels) >= MIN_SERIES_LEVELS and factor is not None) or (
            len(levels) >= MIN_LEVELS_WITH_CARRIER and with_carrier
        ):
            wells = tuple(state for _, states in levels for state in states)
            return _Series(atom, wells, len(levels), factor)
    return None


def _levels(points: list[tuple[float, WellState]]) -> list[tuple[float, list[WellState]]]:
    """Group concentrations that are the same within the tolerance, strongest first."""
    levels: list[tuple[float, list[WellState]]] = []
    for concentration, state in sorted(points, key=lambda p: -p[0]):
        if levels and concentration >= levels[-1][0] * (1 - SERIES_TOLERANCE):
            levels[-1][1].append(state)
        else:
            levels.append((concentration, [state]))
    return levels


def _constant_factor(tops: list[float]) -> float | None:
    """The factor between successive levels, when every step is the same within the tolerance."""
    if len(tops) < 2:
        return None
    factors = [above / below for above, below in zip(tops, tops[1:], strict=False)]
    first = factors[0]
    if all(abs(f - first) <= SERIES_TOLERANCE * first for f in factors):
        return first
    return None


# -- no_rt_control -------------------------------------------------------------------------------


def _no_rt_control(
    facts: Facts, kinds: _Kinds, plate: _Plate, reaction: list[WellState]
) -> list[Finding]:
    rts = kinds.rt - kinds.mix  # an RT word only in the mix's own name says nothing here
    with_rt = [s for s in reaction if any(a in rts for a in _bulk(s))]
    if not with_rt:
        return []

    def contents(state: WellState, without: set[WellKey]) -> frozenset[str]:
        return frozenset(
            kinds.name(a) for a in _bulk(state) if a not in without and kinds.role(a) != "carrier"
        )

    controls = {contents(s, set()) for s in plate.wells if not any(a in rts for a in _bulk(s))}
    if any(contents(s, rts) in controls for s in with_rt):
        return []  # a no-RT well exists
    events = _first_bulk_event(facts.run, rts, with_rt)
    if not events:
        return []
    first = facts.event(events[0])
    wells = facts.refs(s.well for s in with_rt)
    rt_words = listing(sorted({kinds.name(a) for s in with_rt for a in _bulk(s) if a in rts}))
    return [
        _finding(
            facts,
            f"No no-RT control: {well_count(wells)} of {rt_words} with a sample",
            (
                f"At line {first.line} the robot starts putting {rt_words} into "
                f"{_plate_words(wells)}, and {well_count(wells)} end holding it together with a "
                "sample. No well on this plate holds the same sample and reagents without it, "
                "so there is no no-RT control: a signal from genomic DNA left in the sample "
                "cannot be told from the cDNA the reverse transcriptase made."
            ),
            f"Add one well per sample without {rt_words}, and tell the plate map where it is.",
            events,
            wells,
        )
    ]


# -- words and the finding -------------------------------------------------------------------------


def _plate_words(wells: tuple[WellRef, ...]) -> str:
    return f"{wells[0].labware} (slot {wells[0].slot})"


def _finding(
    facts: Facts,
    title: str,
    explanation: str,
    fix: str,
    events: list[int],
    wells: tuple[WellRef, ...],
) -> Finding:
    first = facts.event(events[0])
    return Finding(
        rule_id=RULE_ID,
        family=RULE.family,
        tier=RULE.tier,
        severity="note",
        certain=True,
        roles_basis="declared",
        title=title,
        explanation=explanation + f" Wells: {well_listing(wells)}.",
        fix=fix,
        line=first.line,
        stack=tuple(first.stack),
        occurrences=facts.occurrences(events),
        wells=wells,
        downstream=Downstream(0, ()),
        sources=RULE.sources,
    )


RULE = Rule(
    rule_id=RULE_ID,
    family=6,
    tier="role",
    title="No negative control",
    description=(
        "A PCR or qPCR plate has no well with the mix and no sample: note. The plate counts as "
        "a PCR plate when a master mix or polymerase and samples end up together in at least "
        "four wells. A dilution series of one sample has no "
        "well of diluent without sample: note. A reverse transcriptase reaches the reaction "
        "wells and no well has the same contents without it: note. Silent when no liquids are "
        "declared, and under four reaction wells."
    ),
    sources=(
        sources.MIQE_2009,
        sources.MIQE_2_0,
        sources.BUSTIN_2025,
        sources.QIAGEN_PCR_CONTROLS,
        sources.BIO_RAD_QPCR_GUIDE,
        sources.THERMO_MAXIMA_SYBR,
    ),
    check=check,
)
