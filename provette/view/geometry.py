"""Where things are on the deck, in millimetres, read from the Opentrons definitions.

The trace says which labware sits in which slot and how deep its wells are, but not where each
well is on the plate. That comes from the labware definition shipped with `opentrons_shared_data`
(or from a custom labware folder), chosen as the version whose wells match the trace's geometry
exactly. When no definition matches, the wells are laid out on a regular grid from their names
and the labware is marked `measured: False`, so the page can say the positions are not real.

Deck coordinates: x to the right, y towards the back of the robot, origin at the front-left of
slot 1. The page flips y when it draws.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from provette.model import Labware, WellGeometry

TOLERANCE_MM = 1e-6
DECK_NAME = "ot2_standard"
DECK_VERSION = 5
SLOT_IDS = tuple(str(n) for n in range(1, 13))


@dataclass(frozen=True)
class Slot:
    id: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class WellPosition:
    """The well's centre, from the labware's front-left corner."""

    x: float
    y: float


@dataclass(frozen=True)
class Footprint:
    """The labware's outline and where its wells are, from its definition or a grid."""

    width: float
    height: float
    offset_x: float  # cornerOffsetFromSlot
    offset_y: float
    wells: dict[str, WellPosition]
    measured: bool  # True when read from a definition whose wells match the trace


def deck_slots() -> list[Slot]:
    """The twelve slots of the OT-2, from the deck definition. The fixed trash is a bin that
    rises above slot 12; the page draws it as slot 12's box."""
    from opentrons_shared_data.deck import load

    definition = load(DECK_NAME, DECK_VERSION)
    cutouts = {c["id"]: c["position"] for c in definition["locations"]["cutouts"]}
    areas = {a["id"]: a for a in definition["locations"]["addressableAreas"]}
    slots = []
    for slot_id in SLOT_IDS:
        area = areas[slot_id]
        cutout = cutouts[f"cutout{slot_id}"]
        offset = area.get("offsetFromCutoutFixture", [0, 0, 0])
        box = area["boundingBox"]
        slots.append(
            Slot(
                slot_id,
                cutout[0] + offset[0],
                cutout[1] + offset[1],
                box["xDimension"],
                box["yDimension"],
            )
        )
    return slots


def footprint(labware: Labware, labware_dirs: Sequence[Path], slot: Slot) -> Footprint:
    """The labware's outline and well positions: from a matching definition, else a grid."""
    for definition in _candidates(labware.load_name, labware_dirs):
        if _matches(definition, labware.wells):
            corner = definition.get("cornerOffsetFromSlot", {})
            return Footprint(
                width=float(definition["dimensions"]["xDimension"]),
                height=float(definition["dimensions"]["yDimension"]),
                offset_x=float(corner.get("x", 0.0)),
                offset_y=float(corner.get("y", 0.0)),
                wells={
                    name: WellPosition(float(well["x"]), float(well["y"]))
                    for name, well in definition["wells"].items()
                },
                measured=True,
            )
    return grid(labware.wells, slot.width, slot.height)


def _candidates(load_name: str, labware_dirs: Sequence[Path]) -> list[dict[str, Any]]:
    """Every definition with this load name: custom folders first, then the shipped ones,
    newest version first."""
    found: list[dict[str, Any]] = []
    for directory in labware_dirs:
        for path in sorted(directory.glob("*.json")):
            try:
                definition = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if definition.get("parameters", {}).get("loadName") == load_name:
                found.append(definition)
    from opentrons_shared_data.labware import list_definitions, load_definition

    shipped = [
        (version, schema)
        for name, version, schema in list_definitions()
        if name == load_name and schema in (2, 3)
    ]
    for version, schema in sorted(shipped, reverse=True):
        found.append(dict(load_definition(load_name, version, schema)))
    return found


def _matches(definition: dict[str, Any], wells: dict[str, WellGeometry]) -> bool:
    rows = definition.get("wells", {})
    if set(rows) != set(wells):
        return False
    for name, geometry in wells.items():
        row = rows[name]
        pairs = [
            (row.get("depth"), geometry.depth_mm),
            (row.get("totalLiquidVolume"), geometry.max_volume_ul),
            (row.get("diameter"), geometry.diameter_mm),
            (row.get("xDimension"), geometry.x_mm),
            (row.get("yDimension"), geometry.y_mm),
        ]
        if row.get("shape") != geometry.shape:
            return False
        for theirs, ours in pairs:
            if (theirs is None) != (ours is None):
                return False
            if theirs is not None and abs(float(theirs) - float(ours or 0)) > TOLERANCE_MM:
                return False
    return True


_WELL_NAME = re.compile(r"^([A-Za-z]+)(\d+)$")


def grid(wells: dict[str, WellGeometry], width: float, height: float) -> Footprint:
    """Wells on a regular grid from their names (row letters, column numbers), centred in a
    footprint the size of the slot. Used only when no definition matches."""
    parsed: dict[str, tuple[str, int]] = {}
    for name in wells:
        match = _WELL_NAME.match(name)
        parsed[name] = (match.group(1).upper(), int(match.group(2))) if match else ("A", 1)
    rows = sorted({row for row, _ in parsed.values()})
    cols = sorted({col for _, col in parsed.values()})
    pitch_x = width / (len(cols) + 1)
    pitch_y = height / (len(rows) + 1)
    positions = {}
    for name, (row, col) in parsed.items():
        r = rows.index(row)
        c = cols.index(col)
        positions[name] = WellPosition((c + 1) * pitch_x, height - (r + 1) * pitch_y)
    if not wells:
        positions = {}
    return Footprint(width, height, 0.0, 0.0, positions, measured=False)
