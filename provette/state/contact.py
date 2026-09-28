"""The contact model (DECISIONS.md D-12): did the tip touch the liquid?

Pure functions of numbers. Every assumption made here has a row, with its reason, in the table
of `provette/state/README.md`; change the two together.
"""

from __future__ import annotations

import math
from bisect import bisect_right

from provette.model import WellGeometry
from provette.state.types import Reason, Verdict

# A tip this far above the modelled surface still counts as touching it: the meniscus climbs
# the tip, and the height in the trace is rounded to 0.01 mm.
CONTACT_TOLERANCE_MM = 0.1

# Volumes at or below this are "no liquid". It only absorbs floating-point dust.
EMPTY_UL = 1e-9


def area_mm2(geometry: WellGeometry) -> float | None:
    """Cross-section of the well treated as a straight-sided column, or None if not given."""
    if geometry.shape == "circular" and geometry.diameter_mm:
        return math.pi * (geometry.diameter_mm / 2) ** 2
    if geometry.shape == "rectangular" and geometry.x_mm and geometry.y_mm:
        return geometry.x_mm * geometry.y_mm
    return None


def surface_mm(geometry: WellGeometry | None, volume_ul: float | None) -> float | None:
    """Liquid height above the well bottom, never above the well top.

    With the definition's volume-to-height table (`height_at_ul`), read off the table, straight
    lines between its rows. Without it, volume / area as if the well were a straight column:
    1 uL is 1 mm3, so uL / mm2 is mm. None when the volume or the geometry is unknown.
    """
    if geometry is None or volume_ul is None:
        return None
    volume = max(volume_ul, 0.0)
    if geometry.height_at_ul:
        return min(_interpolated(geometry.height_at_ul, volume), geometry.depth_mm)
    area = area_mm2(geometry)
    if area is None:
        return None
    return min(volume / area, geometry.depth_mm)


def _interpolated(table: list[tuple[float, float]], volume: float) -> float:
    """Height at `volume` from rows of (volume, height) that rise from (0, 0) to the brim."""
    if volume >= table[-1][0]:
        return table[-1][1]
    position = bisect_right(table, (volume, math.inf))
    v0, h0 = table[position - 1]
    v1, h1 = table[position]
    return h0 if v1 == v0 else h0 + (h1 - h0) * (volume - v0) / (v1 - v0)


def volume_at_mm(geometry: WellGeometry | None, height_mm: float) -> float | None:
    """The volume a well holds when its surface is at `height_mm`: the inverse of `surface_mm`.

    None when the geometry is unknown. A rule uses it to say how much liquid a well needs for
    the surface to reach a tip.
    """
    if geometry is None:
        return None
    height = min(max(height_mm, 0.0), geometry.depth_mm)
    if geometry.height_at_ul:
        flipped = [(h, v) for v, h in geometry.height_at_ul]
        return _interpolated(flipped, height)
    area = area_mm2(geometry)
    return None if area is None else height * area


def height_known(geometry: WellGeometry | None) -> bool:
    """Is the surface an exact height rather than a floor? True with a table or a flat bottom."""
    return geometry is not None and geometry.height_known


def at_or_above_top(geometry: WellGeometry | None, height_mm: float | None) -> bool:
    return geometry is not None and height_mm is not None and height_mm >= geometry.depth_mm


def aspirate_contact(
    *,
    is_air_gap: bool,
    geometry: WellGeometry | None,
    height_mm: float | None,
    volume_before_ul: float | None,
    wants_liquid: bool,
) -> tuple[Verdict, Reason, bool]:
    """Verdict for one channel of an aspirate, and whether it draws liquid (else it draws air).

    `volume_before_ul` is the well's volume when the event began, None if unknown.
    `wants_liquid` is volume_ul > 0.
    """
    if is_air_gap:
        return "no_contact", "air_gap", False
    if at_or_above_top(geometry, height_mm):
        return "no_contact", "tip_at_or_above_well_top", False
    if volume_before_ul is not None and volume_before_ul <= EMPTY_UL:
        return "no_contact", "well_empty", False
    surface = surface_mm(geometry, volume_before_ul)
    below = (
        surface is not None
        and height_mm is not None
        and height_mm <= surface + CONTACT_TOLERANCE_MM
    )
    if below:
        return "contact", "tip_below_surface", wants_liquid
    if not wants_liquid:
        # Nothing is drawn, so nothing proves the tip was in the liquid.
        if volume_before_ul is None:
            return "unknown", "volume_unknown", False
        if surface is None or height_mm is None:
            return "unknown", "no_height" if height_mm is None else "no_geometry", False
        return "no_contact", "tip_above_surface", False
    if volume_before_ul is None:
        return "contact", "draws_liquid_volume_unknown", True
    if surface is None or height_mm is None:
        return "contact", "draws_liquid_height_unknown", True
    if height_known(geometry):
        # The surface is where the definition's shape puts it, and the tip is above it: the
        # pipette draws air. The well keeps its liquid.
        return "no_contact", "tip_above_surface", False
    # The column height is a floor on the real height (conical and round bottoms lift the liquid),
    # so a tip between it and the well top may or may not be in the liquid.
    return "unknown", "tip_above_column_height", True


def dispense_contact(
    *,
    geometry: WellGeometry | None,
    height_mm: float | None,
    volume_after_ul: float | None,
) -> tuple[Verdict, Reason]:
    """Verdict for one channel of a dispense or blow_out.

    `volume_after_ul` is the well's volume once every channel of the event has dispensed: the
    surface rises to meet the tip. None if unknown.
    """
    if at_or_above_top(geometry, height_mm):
        return "no_contact", "tip_at_or_above_well_top"
    if volume_after_ul is None:
        return "unknown", "volume_unknown"
    if volume_after_ul <= EMPTY_UL:
        return "no_contact", "well_empty"
    if height_mm is None:
        return "unknown", "no_height"
    surface = surface_mm(geometry, volume_after_ul)
    if surface is None:
        return "unknown", "no_geometry"
    if height_mm <= surface + CONTACT_TOLERANCE_MM:
        return "contact", "tip_below_surface"
    return "no_contact", "tip_above_surface"
