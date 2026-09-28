"""The trace contract: what one run of a protocol looks like once it has left the simulator.

Everything downstream of `provette.trace` (state, rules, report, the web replay) reads these
types and nothing else. This module imports nothing from Opentrons and must stay that way:
`provette.state` replays a trace with no simulator installed.

A trace is a header (`Deck`: the labware, pipettes and declared liquids) and an ordered list of
`Event`s. On disk it is JSON Lines: line 1 is `{"deck": ...}`, every later line is one event.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class WellKey:
    """One well on the deck. `labware_id` is unique per loaded labware within a run.

    `labware_id` is "<slot>:<load_name>", with the slot as Opentrons prints it ("1".."12"), and
    for labware on a module the slot the module sits in. Tip racks use the same key: a tip's
    identity is the rack well it was picked up from.

    From API 2.16 the trash is a deck area, not labware. The tracer gives it the id
    "<slot>:fixedTrash", a deck row with no wells, and the invented well "A1", so that a
    `drop_tip` always has somewhere to point.
    """

    labware_id: str
    well: str  # "A1"

    def __str__(self) -> str:
        return f"{self.labware_id}[{self.well}]"


# ---------------------------------------------------------------------------------------------
# The deck header
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class WellGeometry:
    """Enough of the labware definition to turn a volume into a liquid height.

    `shape` is "circular" (use `diameter_mm`) or "rectangular" (use `x_mm`, `y_mm`). Without
    more, the state treats the well as a straight-sided column of `depth_mm`; conical bottoms
    make real liquid sit higher than that, so the column under-reports height.

    The two optional fields say more, when the labware definition does:

    * `bottom_shape`: the definition's `wellBottomShape`, "flat", "u" or "v", or None when it
      says nothing. A flat well IS a column, so its height is known.
    * `height_at_ul`: a table of (volume in µl, height in mm) pairs, rising from (0, 0) to the
      brim, worked out from the definition's `innerLabwareGeometry` (the well's real shape,
      section by section). Between two rows the state interpolates. With the table the height
      is known whatever the bottom shape.
    """

    depth_mm: float
    max_volume_ul: float
    shape: Literal["circular", "rectangular"]
    diameter_mm: float | None = None
    x_mm: float | None = None
    y_mm: float | None = None
    bottom_shape: Literal["flat", "u", "v"] | None = None
    height_at_ul: list[tuple[float, float]] | None = None

    @property
    def height_known(self) -> bool:
        """Can the liquid height be computed exactly from a volume, rather than as a floor?"""
        return self.height_at_ul is not None or self.bottom_shape == "flat"

    @property
    def brim_ul(self) -> float | None:
        """What the well holds to its rim, when the definition says: the top of the height table,
        or the column of a flat well. `max_volume_ul` is the maker's stated maximum, usually a
        working volume well below this (the NEST "100 ul" PCR well holds about 217 ul to the rim).
        """
        if self.height_at_ul:
            return self.height_at_ul[-1][0]
        if self.bottom_shape == "flat":
            if self.shape == "circular" and self.diameter_mm:
                return math.pi * (self.diameter_mm / 2) ** 2 * self.depth_mm
            if self.x_mm and self.y_mm:
                return self.x_mm * self.y_mm * self.depth_mm
        return None


@dataclass(frozen=True)
class Labware:
    labware_id: str
    load_name: str
    display_name: str
    slot: str
    is_tiprack: bool
    module: str | None  # "temperatureModuleV2", "thermocyclerModuleV2", ... or None
    label: str | None  # the label the protocol author gave it, if any
    wells: dict[str, WellGeometry]


@dataclass(frozen=True)
class Pipette:
    mount: Literal["left", "right"]
    name: str  # "p300_single_gen2"
    channels: int
    min_volume_ul: float
    max_volume_ul: float


@dataclass(frozen=True)
class LiquidLoad:
    """One `well.load_liquid(...)` call: the only thing a protocol declares about its liquids.

    `load_empty` is recorded as `liquid_name=""` with `volume_ul=0`: the well is KNOWN to be
    empty, which is not the same as a well nothing was said about.
    """

    well: WellKey
    liquid_name: str
    description: str | None
    volume_ul: float
    line: int | None


@dataclass(frozen=True)
class Deck:
    protocol_name: str  # basename of the protocol file
    api_level: str
    opentrons_version: str
    labware: list[Labware]
    pipettes: list[Pipette]
    liquid_loads: list[LiquidLoad]
    schema_version: int = SCHEMA_VERSION


# ---------------------------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------------------------

Op = Literal[
    # liquid and tip primitives: these are what the state machine replays
    "pick_up_tip",
    "drop_tip",  # includes return_tip; `returned` says which
    "aspirate",
    "dispense",
    "blow_out",
    "touch_tip",
    # time and environment
    "delay",
    "pause",
    "set_temperature",  # temperature module, thermocycler block, heater-shaker
    "deactivate",
    "thermocycler_profile",
    "lid",  # thermocycler or heater-shaker latch/lid: `detail` says open/close
    "move_labware",
    # anything else the broker reports, kept so nothing is silently dropped. This includes the
    # wrapper calls themselves (TRANSFER, MIX, AIR_GAP, RETURN_TIP...), whose primitives follow
    # as events of their own with `parent` set; and magnet and shaker commands. Replay skips it.
    "other",
]


@dataclass(frozen=True)
class Target:
    """One channel of one action: which tip, in which well.

    A single-channel pipette has one target per event. An 8-channel pipette has eight, in channel
    order, already expanded to the eight wells it actually enters (DECISIONS.md D-11). For
    `pick_up_tip`, `well` is the tip rack well and equals `tip`.
    """

    tip: WellKey | None  # None only if the protocol acts with no tip on
    well: WellKey


@dataclass(frozen=True)
class Event:
    index: int  # 0-based position in the trace
    op: Op
    line: int | None  # line in the protocol file that caused it (innermost protocol frame)
    stack: list[str]  # protocol frames, outermost first: ["run:41", "add_mix:17"]
    parent: str | None  # the enclosing high-level call, lower case: "transfer", "mix",
    # "distribute", "consolidate", "air_gap", or None for a bare primitive
    mount: Literal["left", "right"] | None
    targets: list[Target]
    volume_ul: float | None  # per channel
    height_mm: float | None  # tip height above the well bottom; None if not in a well
    t_est_s: float  # estimated seconds since the start of the run, before this event
    duration_s: float | None  # for delay; None otherwise
    celsius: float | None  # for set_temperature
    module: str | None  # module model the event is about, for environment ops
    labware_id: str | None  # labware the environment op affects, if known
    returned: bool = False  # drop_tip only: the tip went back to its rack
    detail: str = ""  # the simulator's own text for the step
    raw_op: str = ""  # the broker's name, e.g. "command.ASPIRATE"


@dataclass(frozen=True)
class Trace:
    deck: Deck
    events: list[Event] = field(default_factory=list)

    # -- JSON Lines -----------------------------------------------------------------------

    def dump(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"deck": asdict(self.deck)}) + "\n")
            for event in self.events:
                fh.write(json.dumps(asdict(event)) + "\n")

    @staticmethod
    def load(path: Path) -> Trace:
        with path.open(encoding="utf-8") as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
        return Trace(deck=_deck(lines[0]["deck"]), events=[_event(row) for row in lines[1:]])


def _well_key(row: dict[str, Any] | None) -> WellKey | None:
    return None if row is None else WellKey(**row)


def _geometry(row: dict[str, Any]) -> WellGeometry:
    table = row.get("height_at_ul")
    if table is not None:
        row = {**row, "height_at_ul": [(float(v), float(h)) for v, h in table]}
    return WellGeometry(**row)


def _deck(row: dict[str, Any]) -> Deck:
    labware = [
        Labware(**{**lw, "wells": {k: _geometry(g) for k, g in lw["wells"].items()}})
        for lw in row["labware"]
    ]
    loads = [LiquidLoad(**{**ld, "well": WellKey(**ld["well"])}) for ld in row["liquid_loads"]]
    return Deck(
        **{
            **row,
            "labware": labware,
            "pipettes": [Pipette(**p) for p in row["pipettes"]],
            "liquid_loads": loads,
        }
    )


def _event(row: dict[str, Any]) -> Event:
    targets = [Target(tip=_well_key(t["tip"]), well=WellKey(**t["well"])) for t in row["targets"]]
    return Event(**{**row, "targets": targets})
