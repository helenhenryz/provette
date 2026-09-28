"""How far a proposed plate map agrees with a reference one, written for the same request.

Two maps written by different hands name their liquids differently ("pcr_mix" against
"master_mix"), split the same wells into different groups, and may accept different readings
of the request. So the comparison is structural:

1. liquids: each reference liquid is matched to a proposed one of the same kind (role, bind,
   count) whose pattern recognises the other's name, and the proposal's contents are renamed
   into the reference's names;
2. amounts: for the best pair of variants, every reference well (pinned or a group member)
   must have a proposed well with the same contents, within `tolerance_ul`, wherever it sits;
3. positions: the pinned wells must be the same wells, and the free members must carry the
   same constraints (`within`, `position`, `order_hint`).

`agree(proposed, reference)` returns a dict that says so, with what did not match, ready to be
written as JSON.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from provette.intent.compare import tolerance_ul
from provette.intent.spec import Contents, LiquidSpec, PlateMap, Variant

Constraint = tuple[str, frozenset[str] | None, str | None]


def agree(proposed: PlateMap, reference: PlateMap) -> dict[str, Any]:
    liquids = match_liquids(proposed, reference)
    best: dict[str, Any] | None = None
    for ref_variant in reference.variants:
        for prop_variant in proposed.variants:
            candidate = compare_variants(proposed, prop_variant, ref_variant, liquids["renames"])
            if best is None or candidate["score"] > best["score"]:
                best = candidate
    assert best is not None  # a valid map has at least one variant
    return {
        "liquids": {k: v for k, v in liquids.items() if k != "renames"},
        "variants": {"proposed": len(proposed.variants), "reference": len(reference.variants)},
        "best_pair": {"proposed": best["proposed"], "reference": best["reference"]},
        "amounts": best["amounts"],
        "positions": best["positions"],
        "agree": liquids["agree"] and best["amounts"]["agree"] and best["positions"]["agree"],
    }


# ---------------------------------------------------------------------------------------------
# 1. liquids
# ---------------------------------------------------------------------------------------------


def probe_name(spec: LiquidSpec) -> str:
    """The name a protocol would give this liquid: 'master mix', 'sample 1', 'source B3'."""
    if spec.bind == "indexed":
        return f"{spec.stem.replace('_', ' ')} 1"
    if spec.bind == "well":
        return f"{spec.stem} B3"
    return spec.name.replace("_", " ")


def _recognises(spec: LiquidSpec, name: str) -> bool:
    match = re.search(spec.pattern, name)
    if match is None:
        return False
    return spec.bind != "indexed" or match.group(1).isdigit()


def _same_kind(a: LiquidSpec, b: LiquidSpec) -> bool:
    """The same bind and, for numbered samples, the same count; the role is judged after."""
    return a.bind == b.bind and (a.bind != "indexed" or a.count == b.count)


def match_liquids(proposed: PlateMap, reference: PlateMap) -> dict[str, Any]:
    """Reference liquid name -> proposed liquid name, and what could not be matched."""
    pairs: dict[str, str] = {}
    taken: set[str] = set()
    for ref in reference.liquids:
        candidates = [p for p in proposed.liquids if _same_kind(p, ref) and p.name not in taken]
        candidates.sort(key=lambda p: p.role != ref.role)  # the same role first
        exact = [p for p in candidates if p.name == ref.name]
        by_pattern = [
            p
            for p in candidates
            if _recognises(p, probe_name(ref)) or _recognises(ref, probe_name(p))
        ]
        by_kind = candidates if ref.bind == "well" else []
        for pool in (exact, by_pattern, by_kind):
            if pool:
                pairs[ref.name] = pool[0].name
                taken.add(pool[0].name)
                break
    renames = {proposed_name: ref_name for ref_name, proposed_name in pairs.items()}
    differences = []
    for ref in reference.liquids:
        if ref.name in pairs:
            prop = next(p for p in proposed.liquids if p.name == pairs[ref.name])
            if ref.role != prop.role:
                differences.append(
                    f"{ref.name}: role {prop.role!r} proposed ({prop.name}), {ref.role!r} expected"
                )
            if ref.bind == "indexed" and ref.index != prop.index:
                differences.append(
                    f"{ref.name}: index {prop.index!r} proposed, {ref.index!r} expected"
                )
    used = {logical for v in proposed.variants for logical in v.logical_liquids()}
    unmatched_proposed = [
        p.name
        for p in proposed.liquids
        if p.name not in taken and any(p.owns(logical) for logical in used)
    ]
    unmatched_reference = [r.name for r in reference.liquids if r.name not in pairs]
    return {
        "matched": pairs,
        "unmatched_reference": unmatched_reference,
        "unmatched_proposed": unmatched_proposed,
        "differences": differences,
        "agree": not unmatched_reference and not unmatched_proposed and not differences,
        "renames": renames,
    }


def rename(contents: Contents, proposed: PlateMap, renames: Mapping[str, str]) -> dict[str, Any]:
    """The proposal's contents in the reference's liquid names; an unmatched liquid keeps its
    name with a '?' in front, so it can never match."""
    out: dict[str, Any] = {}
    for logical, amount in contents.items():
        spec = proposed.spec_of(logical)
        target = renames.get(spec.name) if spec is not None else None
        if spec is None or target is None:
            out["?" + logical] = amount
        elif spec.bind == "indexed":
            out[target.replace("{i}", logical.rsplit("_", 1)[1])] = amount
        elif spec.bind == "well":
            out[target.replace("{well}", logical.split("@", 1)[1])] = amount
        else:
            out[target] = amount
    return out


# ---------------------------------------------------------------------------------------------
# 2 and 3. amounts and positions, for one pair of variants
# ---------------------------------------------------------------------------------------------


def same_contents(a: Contents, b: Contents) -> bool:
    if set(a) != set(b):
        return False
    for logical, want in a.items():
        have = b[logical]
        if want == "declared" or have == "declared":
            if want != have:
                return False
        elif abs(float(have) - float(want)) > tolerance_ul(float(want)) + 1e-9:
            return False
    return True


def _members(variant: Variant) -> list[tuple[Contents, Constraint]]:
    out: list[tuple[Contents, Constraint]] = []
    for group in variant.groups:
        constraint: Constraint = (
            group.position,
            frozenset(group.within) if group.within is not None else None,
            group.order_hint,
        )
        out += [(member, constraint) for member in group.members]
    return out


def _wells(variant: Variant) -> list[tuple[Contents, str | None, Constraint | None]]:
    """Every expected well: (contents, pinned well or None, group constraint or None)."""
    pinned: list[tuple[Contents, str | None, Constraint | None]] = [
        (contents, well, None) for well, contents in variant.pinned.items()
    ]
    return pinned + [(contents, None, constraint) for contents, constraint in _members(variant)]


def compare_variants(
    proposed_map: PlateMap, proposed: Variant, reference: Variant, renames: Mapping[str, str]
) -> dict[str, Any]:
    """Match every reference well to a proposed well by contents, then judge the positions."""
    prop_wells = [
        (rename(contents, proposed_map, renames), well, constraint)
        for contents, well, constraint in _wells(proposed)
    ]
    ref_wells = _wells(reference)
    free = list(range(len(prop_wells)))
    unmatched_reference: list[str] = []
    pinned_differences: list[str] = []
    constraint_differences: list[str] = []
    matched = 0
    for contents, well, constraint in ref_wells:
        # a pinned reference well prefers the proposed well of the same name
        order = sorted(free, key=lambda k: prop_wells[k][1] != well) if well else free
        hit = next((k for k in order if same_contents(contents, prop_wells[k][0])), None)
        if hit is None:
            unmatched_reference.append(_describe(contents, well))
            continue
        free.remove(hit)
        matched += 1
        prop_well, prop_constraint = prop_wells[hit][1], prop_wells[hit][2]
        if well is not None and prop_well != well:
            pinned_differences.append(
                f"{well} pinned in the reference; proposed "
                + (f"pinned in {prop_well}" if prop_well else "free")
            )
        elif well is None and prop_well is not None:
            pinned_differences.append(f"free in the reference; proposed pinned in {prop_well}")
        elif constraint is not None and prop_constraint != constraint:
            constraint_differences.append(
                f"{_describe(contents, None)}: {_constraint(prop_constraint)} proposed, "
                f"{_constraint(constraint)} expected"
            )
    unmatched_proposed = [_describe(prop_wells[k][0], prop_wells[k][1]) for k in free]
    amounts = {
        "reference_wells": len(ref_wells),
        "proposed_wells": len(prop_wells),
        "matched": matched,
        "unmatched_reference": unmatched_reference[:8],
        "unmatched_proposed": unmatched_proposed[:8],
        "agree": not unmatched_reference and not unmatched_proposed,
    }
    positions = {
        "reference_pinned": len(reference.pinned),
        "proposed_pinned": len(proposed.pinned),
        "pinned_differences": _squeeze(pinned_differences),
        "constraint_differences": _squeeze(constraint_differences),
        # the same number of pinned wells too: differences are only seen on matched wells
        "agree": (
            not pinned_differences
            and not constraint_differences
            and len(reference.pinned) == len(proposed.pinned)
        ),
    }
    return {
        "proposed": proposed.name,
        "reference": reference.name,
        "score": matched - len(unmatched_proposed) - len(pinned_differences),
        "amounts": amounts,
        "positions": positions,
    }


def _describe(contents: Contents, well: str | None) -> str:
    body = " + ".join(
        f"{amount if amount == 'declared' else f'{float(amount):g} ul'} {logical}"
        for logical, amount in contents.items()
    )
    return f"{well}: {body}" if well else body


def _constraint(constraint: Constraint | None) -> str:
    if constraint is None:
        return "pinned"
    position, within, order_hint = constraint
    parts = [position]
    if within is not None:
        parts.append(f"within {len(within)} wells")
    if order_hint:
        parts.append(f"order_hint {order_hint}")
    return ", ".join(parts)


def _squeeze(lines: list[str]) -> list[str]:
    """Many lines that differ only in well name or number are one line with a count."""
    counts: dict[str, int] = {}
    for line in lines:
        key = re.sub(r"\b[A-H]\d{1,2}\b", "<well>", re.sub(r"_\d+\b", "_N", line))
        counts[key] = counts.get(key, 0) + 1
    return [f"{key} (x{n})" if n > 1 else key for key, n in counts.items()][:8]
