"""What a labware definition says about the shape of a well, as a `provette.model.WellGeometry`.

Only the tracer's worker calls this: it runs inside the simulator's process, so it may use the
pinned `opentrons` package. Two things are read beyond the well's outline:

* `wellBottomShape` ("flat", "u" or "v"), which the definition keeps on the group of wells.
* `innerLabwareGeometry`: the well's real shape as a stack of sections (a cone, a box, a sphere
  cap, each with a top and bottom height), from which a volume becomes a height. Opentrons ships
  the maths for these sections (`inner_well_math_utils`, the code its liquid tracking runs on);
  this module only samples that maths into a small table, so that the state, which never
  imports Opentrons, can interpolate.

Which definition carries the shape. A protocol at API 2.19 loads version 2 of the NEST 195 ml
reservoir, and the shape was added in version 4: at 2.19 only 26 of the 137 standard labware
carry it, in their newest versions 73 do. So when the loaded definition has no shape, the
newest version of the same standard labware is read for it (D-14). The well's outline (depth,
maximum volume) stays that of the loaded definition, which is what the tip heights in the trace
are measured against.
"""

from __future__ import annotations

from functools import cache
from typing import Any, Literal, cast

from provette.model import WellGeometry

STANDARD_NAMESPACE = "opentrons"
POINTS_PER_SECTION = 6  # heights sampled per section of the well; the tables stay small

BottomShape = Literal["flat", "u", "v"]
Table = list[tuple[float, float]]


def well_geometry(definition: dict[str, Any], well_name: str) -> WellGeometry:
    well = definition["wells"][well_name]
    return WellGeometry(
        depth_mm=float(well["depth"]),
        max_volume_ul=float(well["totalLiquidVolume"]),
        shape=well["shape"],
        diameter_mm=well.get("diameter"),
        x_mm=well.get("xDimension"),
        y_mm=well.get("yDimension"),
        bottom_shape=_bottom_shape(definition, well_name),
        height_at_ul=_table(definition, well_name),
    )


def _bottom_shape(definition: dict[str, Any], well_name: str) -> BottomShape | None:
    for group in definition.get("groups", []):
        if well_name in group.get("wells", []):
            shape = group.get("metadata", {}).get("wellBottomShape")
            return cast(BottomShape, shape) if shape in ("flat", "u", "v") else None
    return None


_tables: dict[tuple[str, str, int, str], Table | None] = {}


def _table(definition: dict[str, Any], well_name: str) -> Table | None:
    """The (volume, height) table for one well, or None when no definition gives its shape."""
    shaped = definition if definition.get("innerLabwareGeometry") else _newest_shaped(definition)
    if shaped is None:
        return None
    geometry_id = shaped["wells"].get(well_name, {}).get("geometryDefinitionId")
    if geometry_id is None:
        return None
    key = (
        str(shaped["namespace"]),
        str(shaped["parameters"]["loadName"]),
        int(shaped["version"]),
        str(geometry_id),
    )
    if key not in _tables:
        _tables[key] = _sampled(shaped["innerLabwareGeometry"][geometry_id])
    return _tables[key]


def _newest_shaped(definition: dict[str, Any]) -> dict[str, Any] | None:
    """The newest version of the same standard labware that carries `innerLabwareGeometry`."""
    if definition.get("namespace") != STANDARD_NAMESPACE:
        return None
    return _newest_shaped_standard(str(definition["parameters"]["loadName"]))


@cache
def _newest_shaped_standard(load_name: str) -> dict[str, Any] | None:
    from opentrons_shared_data.labware import list_definitions, load_definition

    versions = sorted(v for name, v, _schema in list_definitions((2,)) if name == load_name)
    for version in reversed(versions):
        candidate = cast(dict[str, Any], load_definition(load_name, version))
        if candidate.get("innerLabwareGeometry"):
            return candidate
    return None


def _sampled(raw: dict[str, Any]) -> Table | None:
    """Sample one shape into (volume µl, height mm) rows, from (0, 0) to the brim.

    Heights are sampled evenly within each section, so the rows are densest where the well is
    narrowest: the bottom, where a tip at the default 1 mm sits. Between two rows the state
    interpolates on a straight line, which sits slightly below the true curve (a well widens as
    it rises), so an interpolated height is never above the truth.
    """
    from opentrons_shared_data.labware.labware_definition import (
        InnerWellGeometry,
        UserDefinedVolumes,
    )

    if "heightToVolumeMap" in raw:  # a table the definition's author measured
        user = UserDefinedVolumes.model_validate(raw)
        rows = sorted((float(pair.volume), float(pair.height)) for pair in user.heightToVolumeMap)
        return [(0.0, 0.0)] + [row for row in rows if row[0] > 0]

    from opentrons.protocol_engine.state import inner_well_math_utils as maths

    shape = InnerWellGeometry.model_validate(raw)
    try:
        capacity = maths.get_well_volumetric_capacity(shape)  # [(top height, volume)] ascending
    except NotImplementedError:  # a section shape Opentrons cannot yet compute
        return None
    heights = [0.0]
    bottom = 0.0
    for top, _volume in capacity:
        step = (top - bottom) / POINTS_PER_SECTION
        heights += [bottom + step * i for i in range(1, POINTS_PER_SECTION)] + [top]
        bottom = top
    table: Table = []
    for height in heights:
        volume = float(maths.find_volume_inner_well_geometry(height, shape))
        table.append((round(volume, 3), round(height, 3)))
    return table
