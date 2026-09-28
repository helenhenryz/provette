"""What the replay produces: the state of wells and tips, and the log of what each event did.

Everything here is a frozen value. The replay never edits a state in place, it replaces it, so a
`WellState` taken from the history is the well exactly as it was and can be kept.

The word *atom* means one origin's material. An atom's id is the `WellKey` of the origin well:
the well that held that liquid before the robot put any liquid anywhere.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from provette.model import LiquidLoad, Op, WellKey

Verdict = Literal["contact", "no_contact", "unknown"]

Reason = Literal[
    # contact
    "tip_below_surface",  # tip height <= liquid height (plus the tolerance)
    "draws_liquid_volume_unknown",  # an aspirate that drew liquid had its tip in the liquid
    "draws_liquid_height_unknown",  # same, where the trace gave no height or no geometry
    # no_contact
    "air_gap",  # the aspirate belongs to an air_gap call
    "tip_at_or_above_well_top",
    "tip_above_surface",
    "well_empty",
    "touches_wall_only",  # touch_tip
    "no_tip",
    # unknown
    "tip_above_column_height",  # aspirate: above the straight-column height, below the top
    "volume_unknown",
    "no_height",
    "no_geometry",
]

Mode = Literal["bulk", "carryover"]

AnomalyKind = Literal[
    "aspirate_exceeds_volume",  # asked for more than the well is known to hold
    "aspirate_from_empty_well",
    "aspirate_above_liquid",  # tip above the modelled surface; see Reason tip_above_column_height
    "dispense_exceeds_held",  # asked to dispense more than the tip holds
    "overflow",  # the well now holds more than its max volume
    "no_tip",  # a liquid action with no tip on
    "tip_not_picked_up",  # a tip acts without a pick_up_tip before it
    "tip_picked_up_twice",  # pick_up_tip of a tip that is already on a pipette
    "tip_dropped_with_liquid",  # amount_ul left the run inside a discarded tip
    "missing_volume",  # an aspirate or dispense with volume_ul None
    "well_not_on_deck",  # the well is not in the deck header, so it has no geometry
    "profile_not_modelled",  # thermocycler_profile: the temperature timeline ignores it
]


# ---------------------------------------------------------------------------------------------
# Origins
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Origin:
    """A well that held liquid before the robot put any there. Its `well` is the atom id.

    `declared`: the protocol called `load_liquid` on it, so `loads` and `initial_volume_ul` are
    known. `implicit`: nothing was declared, but at some point the protocol asks the well for more
    than the robot has put into it, so it was holding something; what, and how much, is not known.
    It is an origin from event 0, by hindsight. `min_initial_volume_ul` is then the least it can
    have held for the run to be possible (see README, "Unknown volumes, and hindsight").
    """

    well: WellKey
    kind: Literal["declared", "implicit"]
    loads: tuple[LiquidLoad, ...]
    initial_volume_ul: float | None
    min_initial_volume_ul: float
    first_drawn_event: int | None  # first aspirate that drew liquid from it

    @property
    def liquid_name(self) -> str | None:
        return " + ".join(load.liquid_name for load in self.loads) or None


# ---------------------------------------------------------------------------------------------
# Wells
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Presence:
    """One atom in one well.

    `volume_ul` is the amount under ideal mixing; 0.0 means a trace (it came on a tip, or inside
    transferred liquid that itself only held a trace); None means the amount cannot be known
    because an unknown volume is involved. `mode` is how it got here, and only ever moves from
    "carryover" to "bulk". `certain` is False while every route that brought it rests on a
    contact verdict of "unknown"; it only ever moves from False to True. `since_event` is the
    event that first brought it, or None for an origin's own liquid.
    """

    volume_ul: float | None
    mode: Mode
    certain: bool
    since_event: int | None


@dataclass(frozen=True)
class WellState:
    """`volume_ul` is None when unknown; `min_volume_ul` is then a lower bound, else the same."""

    well: WellKey
    volume_ul: float | None
    min_volume_ul: float
    atoms: Mapping[WellKey, Presence]
    received_liquid: bool = False  # something was dispensed into it during the run


# ---------------------------------------------------------------------------------------------
# Tips
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Layer:
    """One layer inside a tip: liquid (`atoms` maps atom to volume) or air (`atoms` is None)."""

    volume_ul: float
    atoms: Mapping[WellKey, float | None] | None


@dataclass(frozen=True)
class Residue:
    """An atom that has wetted a tip.

    `source_well` is the well where the tip last met the atom, `since_event` the event at which
    it first did. `certain` is False while every meeting rests on an "unknown" contact verdict; a
    certain source is never replaced by an uncertain one.
    """

    source_well: WellKey
    since_event: int
    certain: bool


@dataclass(frozen=True)
class TipState:
    """A tip, identified by the rack well it came from.

    `layers` is what it holds, in the order drawn: the last layer is nearest the opening and
    leaves first. `status` "parked" means it was returned to its rack and keeps its residue;
    "dropped" means it is gone, and `residue` is what it carried when it went.
    """

    tip: WellKey
    status: Literal["in_use", "parked", "dropped"]
    layers: tuple[Layer, ...]
    residue: Mapping[WellKey, Residue]
    picked_up_event: int

    @property
    def liquid_ul(self) -> float:
        return sum(layer.volume_ul for layer in self.layers if layer.atoms is not None)

    @property
    def air_ul(self) -> float:
        return sum(layer.volume_ul for layer in self.layers if layer.atoms is None)


# ---------------------------------------------------------------------------------------------
# The log
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Contact:
    """Whether one tip touched the liquid of one well during one event, and what moved.

    `liquid_ul` and `air_ul` are what this channel really moved in the model, which differs from
    the event's volume when an anomaly was recorded. `surface_mm` is the modelled liquid height
    the tip was compared with (after the dispense, for a dispense), when it could be computed.
    """

    tip: WellKey | None
    well: WellKey
    verdict: Verdict
    reason: Reason
    tip_height_mm: float | None
    surface_mm: float | None
    liquid_ul: float
    air_ul: float


@dataclass(frozen=True, slots=True)
class Arrival:
    """Event `event_index` brought material of `atom` into `well`, on or in `via_tip`.

    An arrival is logged when the atom first reaches the well, and again if its standing there
    improves: carryover becoming bulk, or uncertain becoming certain. `source_well` is the well
    the tip took the atom from, so arrivals can be followed backwards to the origin.
    `volume_ul` is the amount for a bulk arrival (0.0 for a trace carried inside the liquid, None
    when unknown) and 0.0 for carryover.
    """

    atom: WellKey
    well: WellKey
    mode: Mode
    certain: bool
    volume_ul: float | None
    via_tip: WellKey
    source_well: WellKey
    event_index: int


@dataclass(frozen=True)
class Step:
    """What one event did. `contacts` has one entry per target for the four liquid ops."""

    event_index: int
    op: Op
    t_s: float
    contacts: tuple[Contact, ...]
    arrivals: tuple[Arrival, ...]


@dataclass(frozen=True)
class Anomaly:
    """Something odd that is not an error. Collected, never raised."""

    event_index: int
    kind: AnomalyKind
    well: WellKey | None
    tip: WellKey | None
    amount_ul: float | None = None


@dataclass(frozen=True)
class TempInterval:
    """From `start_s` to `end_s` the labware's module was set to `celsius`; None means ambient."""

    start_s: float
    end_s: float
    celsius: float | None
