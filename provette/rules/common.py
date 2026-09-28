"""What the rules share: the facts worked out once per run, and the words used for wells.

`Facts` answers the questions every contamination rule asks:

* Was this material ever *really* in that well, as liquid put there on purpose, or only as the
  film a tip left behind? (`deliberate`)
* When a tip left material behind in a well, was the tip itself carrying that material from
  real liquid it had been in (a ROOT: this is where the mistake is), or was it only passing on
  a trace it met in an already contaminated well (a consequence of an earlier root)? (`roots`)
* Which wells did the damage reach afterwards? (`consequences`)
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property

from provette.model import Event, Labware, Trace, WellKey
from provette.rules.finding import Occurrence, Severity, WellRef
from provette.rules.roles import Role, role_of
from provette.state import Arrival, Presence, Run, WellState

LIQUID_OPS = ("aspirate", "dispense", "blow_out")


def is_real(presence: Presence | None) -> bool:
    """Real liquid (an amount above zero, or an unknown amount), as opposed to a trace (0.0)."""
    return presence is not None and (presence.volume_ul is None or presence.volume_ul > 0)


@dataclass(frozen=True)
class Move:
    """One channel of one aspirate, dispense or blow-out that moved liquid."""

    event_index: int
    is_aspirate: bool
    tip: WellKey
    well: WellKey
    liquid_ul: float


@dataclass
class Facts:
    trace: Trace
    run: Run
    _labware: dict[str, Labware] = field(init=False)
    _same_line: set[tuple[WellKey, WellKey, int]] = field(init=False, default_factory=set)

    def __post_init__(self) -> None:
        self._labware = {labware.labware_id: labware for labware in self.trace.deck.labware}

    # -- what was really in a well, and since when --------------------------------------------

    @cached_property
    def real_since(self) -> dict[tuple[WellKey, WellKey], int]:
        """(well, atom) -> the first event after which the atom was real liquid in the well.

        -1 means from the start. A pair that is missing was never more than a trace there.
        """
        since: dict[tuple[WellKey, WellKey], int] = {}

        def note(state: WellState, event_index: int) -> None:
            for atom, presence in state.atoms.items():
                if (state.well, atom) not in since and is_real(presence):
                    since[(state.well, atom)] = event_index

        for state in self.run.initial_wells.values():
            note(state, -1)
        for changes in self.run.history.values():
            for event_index, state in changes:
                note(state, event_index)
        return since

    @cached_property
    def _real_names(self) -> dict[WellKey, set[str]]:
        names: dict[WellKey, set[str]] = {}
        for well, atom in self.real_since:
            name = self.liquid_name(atom)
            if name is not None:
                names.setdefault(well, set()).add(name)
        return names

    def liquid_name(self, atom: WellKey) -> str | None:
        origin = self.run.origins.get(atom)
        return origin.liquid_name if origin is not None else None

    def role(self, atom: WellKey) -> Role | None:
        """carrier, sample or reagent, from the declared name; None if undeclared or unplaced."""
        origin = self.run.origins.get(atom)
        if origin is None or not origin.loads:
            return None
        load = origin.loads[0]
        return role_of(load.liquid_name, load.description)

    def carry_severity(self, carried: WellKey, into: WellKey, base: Severity) -> Severity:
        """Severity of carrying `carried` into `into`, given what the structure alone says.

        The table (docs/rule-sources.md, "what may be carried into what"): a carrier carried
        anywhere is a note; a sample carried anywhere keeps the structural severity; a reagent
        carried into a sample or another reagent is at most a warning. Unknown roles change
        nothing.
        """
        what, where = self.role(carried), self.role(into)
        if what == "carrier":
            return "note"
        if what == "reagent" and where is not None:
            return "warning" if base == "error" else base
        return base

    def deliberate(self, well: WellKey, atom: WellKey) -> bool:
        """Is the atom's liquid put into `well` on purpose at any point in the run?

        True when the atom is ever there as real liquid, before or after; and true when a
        liquid declared under the same name is (water from two tubes is still water).
        """
        if (well, atom) in self.real_since:
            return True
        name = self.liquid_name(atom)
        return name is not None and name in self._real_names.get(well, set())

    # -- moves, mixing strokes and draws -------------------------------------------------------

    @cached_property
    def _tip_journeys(self) -> list[list[Move]]:
        """What each tip moved, in order, from the moment it was picked up."""
        journeys: list[list[Move]] = []
        current: dict[WellKey, list[Move]] = {}
        for step in self.run.steps:
            if step.op == "pick_up_tip":
                for target in self.event(step.event_index).targets:
                    current.pop(target.tip or target.well, None)
            if step.op not in LIQUID_OPS:
                continue
            for c in step.contacts:
                if c.tip is None or c.liquid_ul <= 0:
                    continue
                if c.tip not in current:
                    current[c.tip] = []
                    journeys.append(current[c.tip])
                current[c.tip].append(
                    Move(step.event_index, step.op == "aspirate", c.tip, c.well, c.liquid_ul)
                )
        return journeys

    @cached_property
    def moves(self) -> list[Move]:
        """Every move of liquid, in event order; within an event, dispenses first."""
        every = (move for journey in self._tip_journeys for move in journey)
        return sorted(every, key=lambda m: (m.event_index, m.is_aspirate))

    @cached_property
    def strokes(self) -> set[Move]:
        """Mixing strokes: an aspirate whose liquid goes straight back into the same well with
        the same tip, and that dispense. `mix()` is made of these, and so is mixing by hand."""
        strokes: set[Move] = set()
        for journey in self._tip_journeys:
            for move, following in zip(journey, journey[1:], strict=False):
                if move.is_aspirate and not following.is_aspirate and following.well == move.well:
                    strokes.update((move, following))
        return strokes

    @cached_property
    def recipients(self) -> dict[Move, tuple[WellKey, ...]]:
        """For every draw (an aspirate that is not a mixing stroke): where that tip dispensed
        before it next drew liquid."""
        recipients: dict[Move, tuple[WellKey, ...]] = {}
        for journey in self._tip_journeys:
            for position, move in enumerate(journey):
                if not move.is_aspirate or move in self.strokes:
                    continue
                went = []
                for later in journey[position + 1 :]:
                    if later.is_aspirate:
                        break
                    went.append(later.well)
                recipients[move] = tuple(went)
        return recipients

    @cached_property
    def draws(self) -> dict[WellKey, list[int]]:
        """well -> the events that took liquid out of it to somewhere else, in order."""
        draws: dict[WellKey, list[int]] = {}
        for move in self.moves:
            if move.is_aspirate and move not in self.strokes:
                draws.setdefault(move.well, []).append(move.event_index)
        return draws

    def drawn_after(self, well: WellKey, event_index: int) -> bool:
        return any(index > event_index for index in self.draws.get(well, []))

    def is_stock(self, well: WellKey) -> bool:
        """A stock held liquid before the robot put any there, and the protocol takes liquid
        out of it to use elsewhere. A well that is only ever mixed in place is not a stock."""
        return well in self.run.origins and well in self.draws

    # -- roots and consequences ---------------------------------------------------------------

    @cached_property
    def roots(self) -> list[Arrival]:
        """The carry-over arrivals where the tip had itself been in real liquid of that material.

        The state logs an `Arrival` whenever material first reaches a well. Three kinds exist:

        * bulk with a volume: the protocol moved that liquid there. Not a problem in itself.
        * bulk with volume 0.0: a trace that travelled *inside* liquid drawn from a well that
          was already contaminated. A consequence.
        * carry-over: a film on a tip that dipped into the well. This is a root only if the tip
          picked the material up from real liquid. A clean tip that goes through contaminated
          master mix and then touches a well is passing on a trace: also a consequence.
        """
        carried: dict[WellKey, set[WellKey]] = {}  # tip -> atoms it has met as real liquid
        # tip -> origin well -> the lines at which this tip went into that origin well
        visited: dict[WellKey, dict[WellKey, set[tuple[str, ...]]]] = {}
        parked: set[WellKey] = set()
        roots: list[Arrival] = []
        for step, event in zip(self.run.steps, self.trace.events, strict=True):
            if step.op == "pick_up_tip":
                for target in event.targets:
                    tip = target.tip or target.well
                    if tip not in parked:
                        carried[tip] = set()  # a new tip carries nothing
                        visited[tip] = {}
                    parked.discard(tip)
            elif step.op == "drop_tip":
                for target in event.targets:
                    if target.tip is None:
                        continue
                    if event.returned:
                        parked.add(target.tip)  # back in the rack: it keeps what it carries
                    else:
                        carried.pop(target.tip, None)
            if step.op not in LIQUID_OPS:
                continue
            line = stack_key(event)
            for arrival in step.arrivals:
                tip = arrival.via_tip
                if arrival.mode != "carryover" or arrival.atom not in carried.get(tip, ()):
                    continue
                roots.append(arrival)
                if line in visited.get(tip, {}).get(arrival.atom, ()):
                    self._same_line.add((arrival.atom, arrival.well, arrival.event_index))
            for contact in step.contacts:
                if contact.tip is None or contact.verdict == "no_contact":
                    continue
                if contact.well in self.run.origins:
                    lines = visited.setdefault(contact.tip, {}).setdefault(contact.well, set())
                    lines.add(line)
                met = carried.setdefault(contact.tip, set())
                for index in (step.event_index, step.event_index + 1):  # before, and after
                    state = self.run.well_before(contact.well, index)
                    met.update(atom for atom, p in state.atoms.items() if is_real(p))
        return roots

    def treated_alike(self, root: Arrival) -> bool:
        """Does the protocol treat the two wells of this root as holding the same liquid?

        True when nothing was declared about at least one of them, and the very line that put
        the tip into this well also put the same tip into the well the material came from:
        `transfer(300, ethanol[i // 6], sample, new_tip="never")`, with the ethanol split over
        several reservoir wells. One line, one tip: the author is treating them as one liquid.
        If they are, nothing is wrong. If they are different samples it is a mix-up, and only a
        protocol that declares its liquids lets Provette tell. A rule reports these as a note.
        """
        _ = self.roots  # fills `_same_line`
        if self.liquid_name(root.atom) is not None and self.liquid_name(root.well) is not None:
            return False  # both declared, under different names: they are different liquids
        return (root.atom, root.well, root.event_index) in self._same_line

    @cached_property
    def _root_keys(self) -> set[tuple[WellKey, WellKey, int]]:
        return {(a.atom, a.well, a.event_index) for a in self.roots}

    def consequences(self, roots: Iterable[Arrival]) -> list[WellKey]:
        """The wells that the material of these roots reached *because* a tip left it there.

        These are the wells that liquid taken out of a root's well afterwards went to, directly
        or through other wells, and where the material then turned up although the protocol
        never puts it there on purpose. A well where the arrival is a root in its own right (a
        tip that really carried the material dipped in) belongs to that root's finding.
        """
        by_well: dict[WellKey, list[Arrival]] = {}
        for root in roots:
            by_well.setdefault(root.well, []).append(root)
        reached: set[WellKey] = set()
        for root_well, arrivals in by_well.items():
            for well in self._flow_from(root_well, min(a.event_index for a in arrivals)):
                for root in arrivals:
                    later = self.run.first_arrival(root.atom, well)
                    if (
                        later is not None
                        and later.event_index > root.event_index
                        and not self.deliberate(well, root.atom)
                        and (later.atom, later.well, later.event_index) not in self._root_keys
                    ):
                        reached.add(well)
                        break
        return sorted(reached, key=natural)

    @cached_property
    def _touches(self) -> list[tuple[int, bool, WellKey, WellKey]]:
        """(event, is_aspirate, tip, well) for every time a tip took liquid, gave liquid, or
        touched liquid; and (event, False, tip, tip) marks the tip being thrown away."""
        touches = []
        for step, event in zip(self.run.steps, self.trace.events, strict=True):
            if step.op == "drop_tip" and not event.returned:
                touches += [(step.event_index, False, t.tip, t.tip) for t in event.targets if t.tip]
            if step.op not in LIQUID_OPS:
                continue
            for c in step.contacts:
                if c.tip is not None and (c.liquid_ul > 0 or c.verdict != "no_contact"):
                    touches.append((step.event_index, step.op == "aspirate", c.tip, c.well))
        return touches

    def _flow_from(self, root_well: WellKey, root_event: int) -> list[WellKey]:
        """Follow the liquid: every well that got liquid (or a wet tip) from `root_well` from
        `root_event` on, or from a well that did."""
        tainted_wells = {root_well}
        tainted_tips: set[WellKey] = set()
        for event_index, is_aspirate, tip, well in self._touches:
            if event_index < root_event:
                continue  # the draw made by the root event itself already holds the material
            if tip == well:
                tainted_tips.discard(tip)  # thrown away
            elif is_aspirate and well in tainted_wells:
                tainted_tips.add(tip)
            elif tip in tainted_tips:
                tainted_wells.add(well)
        tainted_wells.discard(root_well)
        return sorted(tainted_wells, key=natural)

    # -- events -------------------------------------------------------------------------------

    def event(self, event_index: int) -> Event:
        return self.trace.events[event_index]

    def occurrences(self, event_indices: Iterable[int]) -> tuple[Occurrence, ...]:
        return tuple(Occurrence(i, self.event(i).line) for i in sorted(set(event_indices)))

    # -- words --------------------------------------------------------------------------------

    def ref(self, well: WellKey) -> WellRef:
        labware = self._labware.get(well.labware_id)
        slot = labware.slot if labware else well.labware_id.partition(":")[0]
        shown = (labware.label or labware.display_name) if labware else well.labware_id
        return WellRef(well.labware_id, well.well, slot, shown, self.liquid_name(well))

    def refs(self, wells: Iterable[WellKey]) -> tuple[WellRef, ...]:
        return tuple(self.ref(well) for well in sorted(set(wells), key=natural))


_last: list[Facts] = []  # the facts of the run checked last: every rule of one check shares them


def facts_of(trace: Trace, run: Run) -> Facts:
    if not _last or _last[0].run is not run:
        _last[:] = [Facts(trace, run)]
    return _last[0]


def natural(well: WellKey) -> tuple[str, str, int]:
    """Sort A2 before A10."""
    match = re.fullmatch(r"([A-Za-z]*)(\d*)", well.well)
    row, column = (match.group(1), match.group(2)) if match else (well.well, "")
    return (well.labware_id, row, int(column or 0))


ALIKE_NOTE = (
    " This is only a note, because one and the same line of the protocol sends this tip into "
    "all of these wells, which is what an author does with one reagent split over several "
    "wells. If they hold the same liquid, nothing is wrong. If they hold different samples, "
    "it is a mix-up. The protocol does not declare its liquids, so Provette cannot tell which."
)


def stack_key(event: Event) -> tuple[str, ...]:
    """What groups occurrences into one finding: the same line, reached the same way."""
    return tuple(event.stack) or (f"?:{event.line}",)


def _kind(ref: WellRef) -> str:
    return "tube" if "tube" in ref.labware_id.lower() else "well"


def place(ref: WellRef) -> str:
    """ "tube B1 in slot 2"."""
    return f"{_kind(ref)} {ref.well} in slot {ref.slot}"


def liquid(ref: WellRef) -> str:
    """ "sample 1 (tube B1 in slot 2)", or "the liquid from tube B1 in slot 2" if undeclared."""
    return f"{ref.liquid} ({place(ref)})" if ref.liquid else f"the liquid from {place(ref)}"


def well_with_liquid(ref: WellRef) -> str:
    """ "PCR master mix (tube A1 in slot 2)", or just "tube A1 in slot 2"."""
    return f"{ref.liquid} ({place(ref)})" if ref.liquid else place(ref)


def listing(items: list[str], limit: int = 4) -> str:
    """ "a, b and c"; past `limit`, "a, b, c, d and 5 more"."""
    if len(items) > limit:
        return f"{', '.join(items[:limit])} and {len(items) - limit} more"
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} and {items[-1]}"


def well_count(wells: tuple[WellRef, ...]) -> str:
    """ "3 wells", "1 well"."""
    return f"{len(wells)} well{'s' if len(wells) > 1 else ''}"


def well_listing(refs: Iterable[WellRef], limit: int = 8) -> str:
    """ "wells A2, A3 and A4 in slot 1; tube B2 in slot 2". Every labware gets its own part."""
    by_labware: dict[str, list[WellRef]] = {}
    for ref in refs:
        by_labware.setdefault(ref.labware_id, []).append(ref)
    parts = []
    for group in by_labware.values():
        names = [ref.well for ref in group]
        kind = _kind(group[0]) + ("s" if len(names) > 1 else "")
        parts.append(f"{kind} {listing(names, limit)} in slot {group[0].slot}")
    return "; ".join(parts)


def times(count: int) -> str:
    return "once" if count == 1 else "twice" if count == 2 else f"{count} times"


def group_by_line(facts: Facts, arrivals: Iterable[Arrival]) -> list[list[Arrival]]:
    """One group per root line (and the way it was reached), in the order they first happen."""
    groups: dict[tuple[str, ...], list[Arrival]] = {}
    for arrival in arrivals:
        groups.setdefault(stack_key(facts.event(arrival.event_index)), []).append(arrival)
    return list(groups.values())
