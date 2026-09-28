"""Which wells the channels of a pipette really enter (DECISIONS.md D-11).

The simulator names one well per action: the one under the pipette's first channel. The tips of
an 8-channel pipette sit 9 mm apart in a line running from the back of the deck to the front,
so where the other seven go depends only on the shape of the labware:

* a 96-well plate has wells 9 mm apart: A1 means A1, B1, ... H1;
* a 384-well plate has wells 4.5 mm apart: A1 means A1, C1, E1 ... O1;
* a 12-column reservoir has one long well per column, and its definition carries the quirk
  `centerMultichannelOnWells`: the robot centres the whole row of tips on the well, so all
  eight enter the same well.

One rule covers all three: put each channel where the robot puts it, and look up which well of
the labware definition lies under that point. A channel over no well gets `None`.

This file imports nothing from Opentrons; it reads the labware definition as a plain dict.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

CHANNEL_SPACING_MM = 9.0
_EDGE_TOLERANCE_MM = 0.05


def full_offsets(channels: int) -> list[float]:
    """Each channel's y position relative to the first: 0, -9, -18 ... (towards the front)."""
    return [-CHANNEL_SPACING_MM * i for i in range(channels)]


def channel_wells(
    definition: Mapping[str, Any], well_name: str, offsets: Sequence[float]
) -> list[str | None]:
    """The well under each channel when the pipette is sent to `well_name`.

    `offsets` are the channels' y positions relative to the pipette's first active channel.
    """
    wells: Mapping[str, Mapping[str, Any]] = definition["wells"]
    if len(offsets) == 1:
        return [well_name]
    named = wells[well_name]
    quirks = definition.get("parameters", {}).get("quirks") or []
    if "centerMultichannelOnWells" in quirks:
        # The robot centres the row of tips on the well instead of putting channel 1 over it.
        middle = (max(offsets) + min(offsets)) / 2
        offsets = [o - middle for o in offsets]
    return [_well_at(wells, named["x"], named["y"] + o) for o in offsets]


def _well_at(wells: Mapping[str, Mapping[str, Any]], x: float, y: float) -> str | None:
    for name, well in wells.items():
        dx, dy = abs(x - well["x"]), abs(y - well["y"])
        if well["shape"] == "circular":
            inside = math.hypot(dx, dy) <= well["diameter"] / 2 + _EDGE_TOLERANCE_MM
        else:
            inside = (
                dx <= well["xDimension"] / 2 + _EDGE_TOLERANCE_MM
                and dy <= well["yDimension"] / 2 + _EDGE_TOLERANCE_MM
            )
        if inside:
            return name
    return None
