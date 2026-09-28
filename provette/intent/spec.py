"""The plate map: what a scientist wants each well to hold at the end, as plain data.

A plate map is written from the request, not from the protocol. It says, for one destination
labware, how many microlitres of each STARTING liquid every well should hold once the run is
over, as if every well mixed perfectly. A master mix pooled on the deck still resolves to
so-many microlitres of buffer, enzyme and water per well.

* `liquids`: the logical liquids, and how each is found among the liquids a protocol declares.
    - bind "name":    every declared liquid whose name matches `pattern` is this liquid.
    - bind "indexed": the name is `stem_{i}`; `pattern` has one capture group, the sample
                      number. `index` "number" means the number matters (sample 3 has its own
                      volume or position); "any" means every sample is treated alike, so when
                      the declared names carry no usable number the declared order is used.
    - bind "well":    the name is `stem@{well}`; `stem@B3` is whatever the protocol declares
                      in well B3 of the source labware (the one labware, other than the
                      destination, that declares a matching liquid in every well asked for).
  A declared liquid belongs to the first logical liquid, in list order, that matches it.
* `destination`: "auto" (the labware that fits the map best) or a regex on the labware's
  label, display name or load name.
* `variants`: the readings of the request the map accepts; matching any one verifies.
    - `pinned`: well name -> contents, where the request fixes the position.
    - `groups`: `members` (a list of contents) that may sit in any wells, or any wells
      `within` a set. `position` "same_as_source" asks that each member sits in the well with
      the same name as the well its sample started in ("the matching well").
      `order_hint` "index" is the softer expectation that members appear in list order when
      the plate is read along rows or down columns; breaking it gives a note, not a mismatch.
    - `widened`: set when the variant was added after looking at protocols, with the reason.
* contents: logical liquid -> microlitres, or "declared" (the well starts with that liquid
  and must still hold all of it).
* `discard_intended`: logical liquids the request means to throw away.
* `technique`: the technique word of the request ("PCR setup", "ELISA", ...), copied from it
  by the planner; optional. `provette.intent.labware` reads it to say whether the destination
  is the right kind of plate. A map without it loads as before and that check stays silent.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Amount = float | Literal["declared"]
Contents = Mapping[str, Amount]

_WELL = re.compile(r"^[A-Z]\d{1,2}$")


class PlateMapError(ValueError):
    """The plate map file is not a valid plate map. The message says what and where."""


@dataclass(frozen=True)
class LiquidSpec:
    name: str  # "master_mix", "sample_{i}", "template@{well}"
    role: Literal["sample", "reagent"]
    bind: Literal["name", "indexed", "well"]
    pattern: str
    count: int | None = None  # indexed: how many the request speaks of
    index: Literal["number", "any"] = "number"

    @property
    def stem(self) -> str:
        return self.name.replace("_{i}", "").replace("@{well}", "")

    def owns(self, logical: str) -> bool:
        """Is `logical` ("sample_3", "template@A1", "water") one of this spec's liquids?"""
        if self.bind == "indexed":
            return re.fullmatch(re.escape(self.stem) + r"_\d+", logical) is not None
        if self.bind == "well":
            return re.fullmatch(re.escape(self.stem) + r"@[A-Z]\d{1,2}", logical) is not None
        return logical == self.name


@dataclass(frozen=True)
class Group:
    name: str
    members: tuple[Contents, ...]
    within: tuple[str, ...] | None = None
    position: Literal["free", "same_as_source"] = "free"
    order_hint: Literal["index"] | None = None


@dataclass(frozen=True)
class Variant:
    name: str
    why: str
    pinned: Mapping[str, Contents]
    groups: tuple[Group, ...]
    widened: str | None = None

    def logical_liquids(self) -> set[str]:
        names = {liquid for contents in self.pinned.values() for liquid in contents}
        return names | {liq for g in self.groups for member in g.members for liq in member}


@dataclass(frozen=True)
class Destination:
    select: Literal["auto", "regex"] = "auto"
    pattern: str | None = None


@dataclass(frozen=True)
class PlateMap:
    id: str
    request: str
    liquids: tuple[LiquidSpec, ...]
    destination: Destination
    variants: tuple[Variant, ...]
    discard_intended: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    technique: str | None = None

    def spec_of(self, logical: str) -> LiquidSpec | None:
        return next((spec for spec in self.liquids if spec.owns(logical)), None)

    def logical_liquids(self) -> set[str]:
        return set().union(*(variant.logical_liquids() for variant in self.variants))


# ---------------------------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------------------------


def load_platemap(path: Path) -> PlateMap:
    try:
        row = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PlateMapError(f"{path.name} is not JSON: {error}") from error
    return platemap_from_dict(row)


def dump_platemap(platemap: PlateMap) -> dict[str, Any]:
    return {
        "id": platemap.id,
        "request": platemap.request,
        **({"technique": platemap.technique} if platemap.technique is not None else {}),
        "liquids": [
            {
                "name": s.name,
                "role": s.role,
                "bind": s.bind,
                "pattern": s.pattern,
                **({"count": s.count, "index": s.index} if s.bind == "indexed" else {}),
            }
            for s in platemap.liquids
        ],
        "destination": {
            "select": platemap.destination.select,
            **({"pattern": platemap.destination.pattern} if platemap.destination.pattern else {}),
        },
        "variants": [
            {
                "name": v.name,
                "why": v.why,
                **({"widened": v.widened} if v.widened else {}),
                "pinned": {well: dict(contents) for well, contents in v.pinned.items()},
                "groups": [
                    {
                        "name": g.name,
                        "members": [dict(member) for member in g.members],
                        "within": list(g.within) if g.within is not None else None,
                        "position": g.position,
                        "order_hint": g.order_hint,
                    }
                    for g in v.groups
                ],
            }
            for v in platemap.variants
        ],
        "discard_intended": list(platemap.discard_intended),
        "notes": list(platemap.notes),
    }


def platemap_from_dict(row: Mapping[str, Any]) -> PlateMap:
    try:
        platemap = PlateMap(
            id=str(row["id"]),
            request=str(row.get("request", "")),
            liquids=tuple(_liquid(item) for item in row["liquids"]),
            destination=Destination(**row.get("destination", {"select": "auto"})),
            variants=tuple(_variant(item) for item in row["variants"]),
            discard_intended=tuple(row.get("discard_intended", ())),
            notes=tuple(row.get("notes", ())),
            technique=_technique(row.get("technique")),
        )
    except (KeyError, TypeError) as error:
        raise PlateMapError(f"plate map is missing or misnames a field: {error}") from error
    validate(platemap)
    return platemap


def _technique(value: Any) -> str | None:
    """The technique word as written, or None for a missing, null or blank one."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise PlateMapError(f"technique must be a string, not {value!r}")
    return value.strip() or None


def _liquid(item: Mapping[str, Any]) -> LiquidSpec:
    return LiquidSpec(
        name=item["name"],
        role=item["role"],
        bind=item["bind"],
        pattern=item["pattern"],
        count=item.get("count"),
        index=item.get("index", "number"),
    )


def _variant(item: Mapping[str, Any]) -> Variant:
    groups = tuple(
        Group(
            name=g["name"],
            members=tuple(dict(member) for member in g["members"]),
            within=tuple(g["within"]) if g.get("within") is not None else None,
            position=g.get("position", "free"),
            order_hint=g.get("order_hint"),
        )
        for g in item.get("groups", ())
    )
    pinned = {well: dict(contents) for well, contents in item.get("pinned", {}).items()}
    return Variant(item["name"], item.get("why", ""), pinned, groups, item.get("widened"))


# ---------------------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------------------


def validate(platemap: PlateMap) -> None:
    """Raise `PlateMapError` for anything the comparison could not make sense of."""
    if not platemap.variants:
        raise PlateMapError("a plate map needs at least one variant")
    for spec in platemap.liquids:
        _validate_liquid(spec)
    if platemap.destination.select not in ("auto", "regex"):
        raise PlateMapError(
            f"destination.select must be 'auto' or 'regex', not {platemap.destination.select!r}"
        )
    if platemap.destination.select == "regex":
        _compiles(platemap.destination.pattern or "", "destination")
        if not platemap.destination.pattern:
            raise PlateMapError("destination.select is 'regex' but there is no pattern")
    for variant in platemap.variants:
        if not variant.pinned and not variant.groups:
            raise PlateMapError(f"variant {variant.name!r} expects nothing")
        for well, contents in variant.pinned.items():
            if not _WELL.match(well):
                raise PlateMapError(f"variant {variant.name!r}: {well!r} is not a well name")
            _validate_contents(platemap, contents, f"variant {variant.name!r}, well {well}")
        for group in variant.groups:
            where = f"variant {variant.name!r}, group {group.name!r}"
            if not group.members:
                raise PlateMapError(f"{where} has no members")
            if group.position not in ("free", "same_as_source"):
                raise PlateMapError(f"{where}: unknown position {group.position!r}")
            if group.order_hint not in (None, "index"):
                raise PlateMapError(f"{where}: unknown order_hint {group.order_hint!r}")
            if group.within is not None and len(group.within) < len(group.members):
                raise PlateMapError(f"{where}: more members than wells to put them in")
            for member in group.members:
                _validate_contents(platemap, member, where)
    for logical in platemap.discard_intended:
        if platemap.spec_of(logical) is None:
            raise PlateMapError(
                f"discard_intended names {logical!r}, which is not a liquid of the map"
            )


def _validate_liquid(spec: LiquidSpec) -> None:
    if spec.role not in ("sample", "reagent"):
        raise PlateMapError(f"liquid {spec.name!r}: role must be 'sample' or 'reagent'")
    compiled = _compiles(spec.pattern, f"liquid {spec.name!r}")
    if spec.bind == "indexed":
        if not spec.name.endswith("_{i}") or compiled.groups != 1:
            raise PlateMapError(
                f"liquid {spec.name!r}: an indexed liquid is named 'stem_{{i}}' and its pattern "
                "has exactly one capture group, the sample number"
            )
        if spec.index not in ("number", "any"):
            raise PlateMapError(f"liquid {spec.name!r}: index must be 'number' or 'any'")
    elif spec.bind == "well":
        if not spec.name.endswith("@{well}"):
            raise PlateMapError(f"liquid {spec.name!r}: a by-well liquid is named 'stem@{{well}}'")
    elif spec.bind != "name":
        raise PlateMapError(f"liquid {spec.name!r}: bind must be 'name', 'indexed' or 'well'")


def unknown_liquid_words(platemap: PlateMap, logical: str) -> str:
    """Why a well's liquid is not in the map, naming the liquids that are, and the one-sentence
    fix when the name looks like a by-well ('template@A1') or an indexed ('sample_3') liquid:
    declare the stem in `liquids` with the bind that owns such names."""
    declared = ", ".join(repr(s.name) for s in platemap.liquids) or "none"
    text = f"{logical!r} is not one of the map's liquids (declared: {declared})."
    by_well = re.fullmatch(r"(.+)@[A-Z]\d{1,2}", logical)
    by_index = re.fullmatch(r"(.+)_\d+", logical)
    if by_well:
        text += f" To use it, declare '{by_well.group(1)}@{{well}}' in `liquids` with bind 'well'."
    elif by_index:
        text += f" To use it, declare '{by_index.group(1)}_{{i}}' in `liquids` with bind 'indexed'."
    return text


def _compiles(pattern: str, where: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern)
    except re.error as error:
        raise PlateMapError(f"{where}: the pattern {pattern!r} is not a regex: {error}") from error


def _validate_contents(platemap: PlateMap, contents: Contents, where: str) -> None:
    if not contents:
        raise PlateMapError(f"{where}: an expected well must hold something")
    for logical, amount in contents.items():
        spec = platemap.spec_of(logical)
        if spec is None:
            raise PlateMapError(f"{where}: {unknown_liquid_words(platemap, logical)}")
        if amount == "declared":
            continue
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
            raise PlateMapError(f"{where}: {logical!r} must be a volume above 0 or 'declared'")
        if spec.bind == "indexed" and spec.count is not None:
            number = int(logical.rsplit("_", 1)[1])
            if not 1 <= number <= spec.count:
                raise PlateMapError(f"{where}: {logical!r} is outside 1..{spec.count}")
