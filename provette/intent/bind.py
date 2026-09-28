"""Find the plate map's logical liquids among the liquids a protocol declares.

A binding failure is never silent: it is a `problem`, and a report with problems says "cannot
check" instead of "verified".
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from provette.intent.spec import LiquidSpec, PlateMap
from provette.model import Trace, WellKey
from provette.state import Run


@dataclass(frozen=True)
class Binding:
    atoms_of: Mapping[str, tuple[WellKey, ...]]  # logical liquid -> the origin wells that hold it
    logical_of: Mapping[WellKey, str]  # origin well -> logical liquid
    problems: tuple[str, ...]
    notes: tuple[str, ...]

    def role_of(self, platemap: PlateMap, atom: WellKey) -> str | None:
        logical = self.logical_of.get(atom)
        spec = platemap.spec_of(logical) if logical is not None else None
        return spec.role if spec is not None else None


def bind(trace: Trace, run: Run, platemap: PlateMap) -> Binding:
    wanted = platemap.logical_liquids()
    declared = _declared_in_load_order(trace, run)
    atoms_of: dict[str, list[WellKey]] = {}
    logical_of: dict[WellKey, str] = {}
    problems: list[str] = []
    notes: list[str] = []

    def claim(logical: str, atom: WellKey) -> None:
        atoms_of.setdefault(logical, []).append(atom)
        logical_of[atom] = logical

    for spec in platemap.liquids:
        free = [(atom, name) for atom, name in declared if atom not in logical_of]
        matching = [(atom, name) for atom, name in free if re.search(spec.pattern, name)]
        if spec.bind == "name":
            for atom, _ in matching:
                claim(spec.name, atom)
        elif spec.bind == "indexed":
            numbered = _index(spec, matching, problems, notes)
            for number, atoms in numbered.items():
                for atom in atoms:
                    claim(f"{spec.stem}_{number}", atom)
        else:
            _bind_by_well(spec, matching, trace, wanted, claim, problems)

    for logical in sorted(wanted, key=_natural):
        if logical not in atoms_of and not any(logical in p for p in problems):
            owner = platemap.spec_of(logical)
            pattern = owner.pattern if owner is not None else "?"
            problems.append(
                f"The plate map speaks of '{logical}', but no liquid the protocol declares "
                f"matches it (pattern {pattern}). Declared: {_names(declared)}."
            )
    return Binding(
        {logical: tuple(atoms) for logical, atoms in atoms_of.items()},
        logical_of,
        tuple(_few(problems)),
        tuple(notes),
    )


def _declared_in_load_order(trace: Trace, run: Run) -> list[tuple[WellKey, str]]:
    seen: dict[WellKey, str] = {}
    for load in trace.deck.liquid_loads:
        origin = run.origins.get(load.well)
        if origin is not None and origin.kind == "declared" and origin.liquid_name:
            seen.setdefault(load.well, origin.liquid_name)
    return list(seen.items())


def _index(
    spec: LiquidSpec,
    matching: list[tuple[WellKey, str]],
    problems: list[str],
    notes: list[str],
) -> dict[int, list[WellKey]]:
    """Sample number -> origin wells. One liquid name is one sample, however many wells."""
    by_name: dict[str, list[WellKey]] = {}
    for atom, name in matching:
        by_name.setdefault(name, []).append(atom)
    numbers = {}
    for name in by_name:
        found = re.search(spec.pattern, name)
        numbers[name] = int(found.group(1)) if found and found.group(1) is not None else None
    usable = all(n is not None for n in numbers.values()) and len(set(numbers.values())) == len(
        numbers
    )
    if usable and numbers:
        values = sorted(n for n in numbers.values() if n is not None)
        shift = 1 if values[0] == 0 else 0
        if shift:
            notes.append(f"The protocol numbers its '{spec.stem}' liquids from 0; read as 1-based.")
        return {(numbers[name] or 0) + shift: atoms for name, atoms in by_name.items()}
    if spec.index == "any":
        if by_name:
            notes.append(
                f"The declared '{spec.stem}' liquids carry no usable number; they are taken in "
                "the order the protocol declares them. Every one is treated alike by this "
                "plate map, so which is which does not change what is expected."
            )
        return {i: atoms for i, atoms in enumerate(by_name.values(), start=1)}
    if by_name:
        problems.append(
            f"The plate map gives each '{spec.stem}' its own number, but the declared names "
            f"({_names(matching)}) do not carry distinct numbers, so they cannot be told apart."
        )
    return {}


def _bind_by_well(
    spec: LiquidSpec,
    matching: list[tuple[WellKey, str]],
    trace: Trace,
    wanted: set[str],
    claim: Callable[[str, WellKey], None],
    problems: list[str],
) -> None:
    wells = sorted({logical.split("@", 1)[1] for logical in wanted if spec.owns(logical)})
    if not wells:
        return
    holds: dict[str, dict[str, WellKey]] = {}
    for atom, _ in matching:
        holds.setdefault(atom.labware_id, {})[atom.well] = atom
    candidates = [lw for lw, have in holds.items() if all(well in have for well in wells)]
    if len(candidates) != 1:
        labels = {lw.labware_id: lw.label or lw.display_name for lw in trace.deck.labware}
        if not candidates:
            problems.append(
                f"The plate map takes '{spec.stem}' from wells {_short(wells)} of a source "
                "plate, but no labware declares a liquid in every one of those wells."
            )
        else:
            listed = ", ".join(f"{labels.get(c, c)} (slot {c.split(':')[0]})" for c in candidates)
            problems.append(
                f"More than one labware could be the source of '{spec.stem}': {listed}."
            )
        return
    for well in wells:
        claim(f"{spec.stem}@{well}", holds[candidates[0]][well])


def _natural(text: str) -> tuple[str, int]:
    found = re.search(r"(\d+)$", text)
    return (text[: found.start()] if found else text, int(found.group(1)) if found else 0)


def _names(declared: list[tuple[WellKey, str]]) -> str:
    names = list(dict.fromkeys(name for _, name in declared))
    return _short(names) if names else "nothing"


def _short(items: list[str], most: int = 8) -> str:
    if len(items) <= most:
        return ", ".join(items)
    return ", ".join(items[:most]) + f" and {len(items) - most} more"


def _few(problems: list[str], most: int = 6) -> list[str]:
    if len(problems) <= most:
        return problems
    return problems[:most] + [f"... and {len(problems) - most} more binding problems."]
