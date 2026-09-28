"""The plate-map check: does the replayed protocol leave each well holding what the plate map says?

    report = compare(trace, run, platemap)
    report.status  # "verified", "mismatch" or "cannot_check"

What a well holds is read from the replay: for each logical liquid, the summed volume of the
origin liquids bound to it, under ideal mixing. Carry-over films and traces (volume 0) are the
contamination rules' business and are ignored here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from provette.intent.bind import Binding, bind
from provette.intent.spec import Contents, Group, PlateMap, Variant
from provette.model import Labware, Trace, WellKey
from provette.state import Run

# A liquid counts as really there above this volume. Below it is rounding in the replay.
REAL_UL = 0.01

IssueKind = Literal[
    "wrong_amount",  # the liquid is there, in the wrong volume
    "missing_liquid",  # the map lists it, the well has none
    "unexpected_liquid",  # the well holds a liquid the map does not list for it
    "well_empty",  # a pinned well holds nothing
    "no_well",  # a group member for which no well on the plate can be found
    "unexpected_well",  # a well the map says nothing about holds liquid
    "wrong_position",  # right contents, but not in the well the map asks for
    "amount_unknown",  # the replay cannot know the volume (an undeclared liquid is involved)
]


def tolerance_ul(expected_ul: float) -> float:
    """How far a found volume may be from the expected one and still be 'the same'.

    Measured on the 34 correct protocols (eval/checks/results/tolerance.json): of 2,040 expected
    amounts the furthest off was 0.005 ul (0.10%), a normalisation volume rounded to 0.01 ul.
    So the first setting (the larger of 2% and 0.2 ul) was far wider than any honest protocol
    needs, and 0.2 ul accepts anything at all where little is expected: 0.5 ul of polymerase
    could be 0.3, and the last well of a 12-point dilution (0.05 ul of drug) could hold none.

    Now: 2%, or 0.06 ul if that is larger, which is just over half of the 0.1 ul step a
    protocol may fairly round to; and for amounts under 0.6 ul, which nobody pipettes directly,
    never more than 10% of the amount.
    """
    return max(0.02 * expected_ul, min(0.06, 0.10 * expected_ul))


@dataclass(frozen=True)
class Issue:
    kind: IssueKind
    liquid: str | None = None
    expected_ul: float | None = None
    found_ul: float | None = None
    detail: str = ""


@dataclass(frozen=True)
class WellResult:
    well: str | None  # None: a group member no well could be found for
    group: str | None  # None: a pinned well, or a well the map does not speak of
    expected: Mapping[str, float]
    found: Mapping[str, float]
    issues: tuple[Issue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class IntentReport:
    platemap_id: str
    status: Literal["verified", "mismatch", "cannot_check"]
    destination: str | None  # labware_id
    destination_name: str | None
    variant: str | None
    wells: tuple[WellResult, ...]
    problems: tuple[str, ...]  # why it cannot be checked
    notes: tuple[str, ...]
    binding: Binding

    @property
    def mismatches(self) -> tuple[WellResult, ...]:
        return tuple(result for result in self.wells if not result.ok)

    def dose_ul(self, logical: str) -> float | None:
        """The smallest amount of `logical` the accepted variant wants in any one well."""
        doses = [r.expected[logical] for r in self.wells if r.expected.get(logical)]
        return min(doses, default=None)

    def expected_wells(self, logical: str) -> set[str]:
        """The wells of the destination where the accepted variant wants `logical`."""
        return {r.well for r in self.wells if r.well is not None and logical in r.expected}


def compare(trace: Trace, run: Run, platemap: PlateMap) -> IntentReport:
    binding = bind(trace, run, platemap)
    if binding.problems:
        return IntentReport(
            platemap.id,
            "cannot_check",
            None,
            None,
            None,
            (),
            binding.problems,
            binding.notes,
            binding,
        )
    candidates, problem = _candidate_labware(trace, platemap)
    if problem:
        return IntentReport(
            platemap.id, "cannot_check", None, None, None, (), (problem,), binding.notes, binding
        )
    scored = []
    for labware in candidates:
        found = _found(run, labware, binding)
        received = sum(
            1 for well in labware.wells if _received(run, WellKey(labware.labware_id, well))
        )
        for variant in platemap.variants:
            results, notes = _evaluate(run, binding, platemap, variant, labware, found)
            n_ok = sum(r.ok for r in results)
            # liquids that are at least in the right well, whatever the amount: what tells
            # the destination plate from the others when no well is right
            n_present = sum(1 for r in results for liquid in r.expected if liquid in r.found)
            n_issues = sum(len(r.issues) for r in results)
            scored.append(
                ((n_ok, n_present, -n_issues, received), labware, variant, results, notes)
            )
    scored.sort(key=lambda row: row[0], reverse=True)
    best = scored[0]
    rivals = [row for row in scored if row[0] == best[0] and row[1] is not best[1]]
    if rivals and best[0][:2] == (0, 0):
        tied = {row[1].labware_id: _labware_name(row[1]) for row in [best, *rivals]}
        problem = (
            "Nothing on the deck looks like the plate the map describes, and more than one "
            f"labware fits equally badly ({', '.join(tied.values())}). Name the destination in "
            "the plate map."
        )
        return IntentReport(
            platemap.id, "cannot_check", None, None, None, (), (problem,), binding.notes, binding
        )
    _, labware, variant, results, notes = best
    status: Literal["verified", "mismatch"] = (
        "verified" if all(r.ok for r in results) else "mismatch"
    )
    return IntentReport(
        platemap.id,
        status,
        labware.labware_id,
        _labware_name(labware),
        variant.name,
        tuple(results),
        (),
        (*binding.notes, *notes),
        binding,
    )


# ---------------------------------------------------------------------------------------------
# The destination
# ---------------------------------------------------------------------------------------------


def _labware_name(labware: Labware) -> str:
    return f"{labware.label or labware.display_name} (slot {labware.slot})"


def _candidate_labware(trace: Trace, platemap: PlateMap) -> tuple[list[Labware], str]:
    labware = [lw for lw in trace.deck.labware if not lw.is_tiprack and lw.wells]
    if platemap.destination.select == "regex" and platemap.destination.pattern:
        pattern = platemap.destination.pattern
        named = [
            lw
            for lw in labware
            if any(
                re.search(pattern, text) for text in (lw.label or "", lw.display_name, lw.load_name)
            )
        ]
        if named:
            return named, ""
        return [], (
            f"No labware on the deck has a label or name matching {pattern}, so the destination "
            f"plate cannot be found. On the deck: {', '.join(_labware_name(lw) for lw in labware)}."
        )
    if not labware:
        return [], "The protocol loads no labware with wells."
    return labware, ""


def _received(run: Run, key: WellKey) -> bool:
    state = run.wells.get(key)
    return state is not None and state.received_liquid


# ---------------------------------------------------------------------------------------------
# What a well holds
# ---------------------------------------------------------------------------------------------

UNKNOWN = "?"  # key in a found mapping: some liquid of unknown volume is in the well
# A liquid the protocol DECLARES as already in the well it is found in. A plate map that expects
# the robot to deliver 20 ul of master mix is not satisfied by a protocol that declares the plate
# as arriving full: a small model did exactly that (eval/e4). Only an amount given as "declared"
# in the plate map (standards that are "already in the plate") accepts it.
HERE = " (declared in this well, not delivered)"


def _found(run: Run, labware: Labware, binding: Binding) -> dict[str, dict[str, float]]:
    """Well name -> logical liquid -> ul, for every well of the labware that holds anything."""
    out: dict[str, dict[str, float]] = {}
    for well in labware.wells:
        state = run.wells.get(WellKey(labware.labware_id, well))
        if state is None:
            continue
        contents: dict[str, float] = {}
        for atom, presence in state.atoms.items():
            if presence.volume_ul is None:
                contents[UNKNOWN] = 0.0
            elif presence.volume_ul > REAL_UL:
                name = binding.logical_of.get(atom) or _unbound_name(run, atom)
                if atom == state.well and atom in binding.logical_of:
                    name += HERE  # the protocol declared it in this well; the robot did not put it
                contents[name] = contents.get(name, 0.0) + presence.volume_ul
        if contents:
            out[well] = contents
    return out


def _unbound_name(run: Run, atom: WellKey) -> str:
    origin = run.origins.get(atom)
    if origin is not None and origin.liquid_name:
        return f"[{origin.liquid_name}]"
    return f"[undeclared liquid from {atom.well} in slot {atom.labware_id.split(':')[0]}]"


def _resolve(
    contents: Contents, well: str, labware: Labware, run: Run, binding: Binding
) -> dict[str, float]:
    """Turn "declared" into the volume the protocol declared for that liquid in that well."""
    out = {}
    for logical, amount in contents.items():
        if amount == "declared":
            key = WellKey(labware.labware_id, well)
            origin = run.origins.get(key)
            here = key in binding.atoms_of.get(logical, ())
            out[logical + HERE] = (origin.initial_volume_ul or 0.0) if origin and here else 0.0
        else:
            out[logical] = float(amount)
    return out


def _diff(expected: Mapping[str, float], found: Mapping[str, float]) -> list[Issue]:
    issues = []
    if UNKNOWN in found:
        issues.append(Issue("amount_unknown", detail="an undeclared liquid is in this well"))
    for liquid, want in expected.items():
        have = found.get(liquid, 0.0)
        if have <= REAL_UL:
            issues.append(Issue("missing_liquid", liquid, want, 0.0))
        elif abs(have - want) > tolerance_ul(want) + 1e-9:
            issues.append(Issue("wrong_amount", liquid, want, have))
    for liquid, have in found.items():
        if liquid not in expected and liquid != UNKNOWN:
            issues.append(Issue("unexpected_liquid", liquid, None, have))
    return issues


# ---------------------------------------------------------------------------------------------
# One variant against one labware
# ---------------------------------------------------------------------------------------------


def _evaluate(
    run: Run,
    binding: Binding,
    platemap: PlateMap,
    variant: Variant,
    labware: Labware,
    found: Mapping[str, Mapping[str, float]],
) -> tuple[list[WellResult], list[str]]:
    results: list[WellResult] = []
    notes: list[str] = []
    for well, contents in variant.pinned.items():
        expected = _resolve(contents, well, labware, run, binding)
        if well not in labware.wells:
            results.append(
                WellResult(well, None, expected, {}, (Issue("well_empty", detail="no such well"),))
            )
        elif well not in found:
            results.append(WellResult(well, None, expected, {}, (Issue("well_empty"),)))
        else:
            results.append(
                WellResult(well, None, expected, found[well], tuple(_diff(expected, found[well])))
            )

    free = [well for well in labware.wells if well in found and well not in variant.pinned]
    free.sort(key=_column_major)
    taken: dict[str, tuple[Group, int]] = {}  # well -> the member it was matched to
    open_members: list[tuple[Group, int]] = []

    # 1. Exact: each member takes the first free well that holds exactly what it should.
    for group in variant.groups:
        for number, member in enumerate(group.members):
            for well in free:
                if well in taken or not _allowed(group, well):
                    continue
                expected = _resolve(member, well, labware, run, binding)
                if _diff(expected, found[well]) or _misplaced(
                    group, member, well, binding, platemap
                ):
                    continue
                taken[well] = (group, number)
                results.append(WellResult(well, group.name, expected, found[well], ()))
                break
            else:
                open_members.append((group, number))

    # 2. Nearest: a member left over is paired with the free well that shares most with it,
    #    sample liquids first, so the report can say what is wrong with that well.
    pairs = []
    for group, number in open_members:
        member = group.members[number]
        for well in free:
            if well in taken or not _allowed(group, well):
                continue
            shared = [liquid for liquid in member if liquid in found[well]]
            if not shared:
                continue
            samples = sum(_is_sample(platemap, liquid) for liquid in shared)
            pairs.append(((samples, len(shared)), group, number, well))
    pairs.sort(key=lambda row: (row[0], -_column_major(row[3])[0], row[3]), reverse=True)
    paired: set[tuple[str, int]] = set()
    for _, group, number, well in pairs:
        if well in taken or (group.name, number) in paired:
            continue
        member = group.members[number]
        expected = _resolve(member, well, labware, run, binding)
        issues = _diff(expected, found[well])
        misplaced = _misplaced(group, member, well, binding, platemap)
        if misplaced:
            issues.append(Issue("wrong_position", detail=misplaced))
        taken[well] = (group, number)
        paired.add((group.name, number))
        results.append(WellResult(well, group.name, expected, found[well], tuple(issues)))
    for group, number in open_members:
        if (group.name, number) not in paired:
            expected = {
                k: (0.0 if v == "declared" else float(v)) for k, v in group.members[number].items()
            }
            results.append(WellResult(None, group.name, expected, {}, (Issue("no_well"),)))

    # 3. Anything else on the plate.
    for well in free:
        if well in taken:
            continue
        if _is_untouched_source(run, WellKey(labware.labware_id, well)):
            continue
        results.append(WellResult(well, None, {}, found[well], (Issue("unexpected_well"),)))

    for group in variant.groups:
        note = _order_note(group, {w: n for w, (g, n) in taken.items() if g is group})
        if note:
            notes.append(note)
    return results, notes


def _column_major(well: str) -> tuple[int, str]:
    return (int(well[1:]), well[0])


def _allowed(group: Group, well: str) -> bool:
    return group.within is None or well in group.within


def _is_sample(platemap: PlateMap, logical: str) -> bool:
    spec = platemap.spec_of(logical)
    return spec is not None and spec.role == "sample"


def _misplaced(
    group: Group, member: Contents, well: str, binding: Binding, platemap: PlateMap
) -> str:
    """For "same_as_source": the well the member's sample started in, if it is not this one."""
    if group.position != "same_as_source":
        return ""
    for logical in member:
        if not _is_sample(platemap, logical):
            continue
        sources = {atom.well for atom in binding.atoms_of.get(logical, ())}
        if sources and sources != {well}:
            started = ", ".join(sorted(sources))
            return f"{logical} started in {started} and should be in the same well here"
    return ""


def _is_untouched_source(run: Run, key: WellKey) -> bool:
    """A starting liquid sitting in its own well, with nothing added: a source, not a product."""
    state = run.wells.get(key)
    return state is not None and key in run.origins and not state.received_liquid


def _order_note(group: Group, placed: Mapping[str, int]) -> str:
    """`placed`: well -> member number. Members with the same contents share a rank."""
    if group.order_hint != "index" or len(placed) < 2:
        return ""
    first_with: dict[str, int] = {}
    rank = {}
    for number, member in enumerate(group.members):
        rank[number] = first_with.setdefault(repr(sorted(member.items())), number)
    for reading in (_column_major, lambda well: (ord(well[0]), well[1:].zfill(2))):
        sequence = [rank[placed[well]] for well in sorted(placed, key=reading)]
        if _in_order(sequence):
            return ""
    return (
        f"The {group.name} are all there, but not in the order of their numbers when the plate "
        "is read along rows or down columns. The request does not fix the order, so this is a "
        "note: check that your plate layout sheet matches the protocol, not the numbering."
    )


def _in_order(sequence: list[int]) -> bool:
    """Non-decreasing (1 1 1 2 2 2 ...), or one increasing run repeated (1 2 3 1 2 3 ...)."""
    if all(a <= b for a, b in zip(sequence, sequence[1:], strict=False)):
        return True
    period = len(set(sequence))
    run = sequence[:period]
    return (
        all(a < b for a, b in zip(run, run[1:], strict=False))
        and len(sequence) % period == 0
        and sequence == run * (len(sequence) // period)
    )
