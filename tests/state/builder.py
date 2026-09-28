"""Build a `Trace` by hand, so the state can be tested with no simulator.

The deck is fixed: a tube rack in slot 2, a PCR plate in slot 1, a flat plate in slot 4 sitting
on a temperature module, a reservoir in slot 5 and a tip rack in slot 3. The geometries are the
real ones of the named Opentrons labware, copied by hand.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from provette.model import (
    Deck,
    Event,
    Labware,
    LiquidLoad,
    Op,
    Pipette,
    Target,
    Trace,
    WellGeometry,
    WellKey,
)

TUBE = WellGeometry(depth_mm=37.9, max_volume_ul=1500, shape="circular", diameter_mm=8.7)
PCR = WellGeometry(depth_mm=14.78, max_volume_ul=100, shape="circular", diameter_mm=5.34)
FLAT = WellGeometry(depth_mm=10.67, max_volume_ul=360, shape="circular", diameter_mm=6.86)
TROUGH = WellGeometry(depth_mm=26.85, max_volume_ul=15000, shape="rectangular", x_mm=8.2, y_mm=71.2)

ROWS = "ABCDEFGH"
NAMES_96 = [f"{row}{col}" for col in range(1, 13) for row in ROWS]

RACK_ID = "2:opentrons_24_tuberack_nest_1.5ml_snapcap"
PLATE_ID = "1:nest_96_wellplate_100ul_pcr_full_skirt"
FLAT_ID = "4:corning_96_wellplate_360ul_flat"
TROUGH_ID = "5:nest_12_reservoir_15ml"
TIPS_ID = "3:opentrons_96_tiprack_300ul"

# Heights, in mm above the well bottom.
LOW = 1.0  # where Opentrons aspirates and dispenses by default
ABOVE = 100.0  # above the top of every well on this deck


def tube(name: str) -> WellKey:
    return WellKey(RACK_ID, name)


def plate(name: str) -> WellKey:
    return WellKey(PLATE_ID, name)


def flat(name: str) -> WellKey:
    return WellKey(FLAT_ID, name)


def trough(name: str) -> WellKey:
    return WellKey(TROUGH_ID, name)


def tip(name: str) -> WellKey:
    return WellKey(TIPS_ID, name)


def _labware(labware_id: str, names: Sequence[str], geometry: WellGeometry, **kw: str) -> Labware:
    slot, load_name = labware_id.split(":")
    return Labware(
        labware_id=labware_id,
        load_name=load_name,
        display_name=load_name,
        slot=slot,
        is_tiprack=labware_id == TIPS_ID,
        module=kw.get("module"),
        label=None,
        wells={name: geometry for name in names},
    )


def deck(loads: Mapping[WellKey, tuple[str, float]]) -> Deck:
    tubes = [f"{row}{col}" for col in range(1, 7) for row in "ABCD"]
    return Deck(
        protocol_name="hand_built.py",
        api_level="2.15",
        opentrons_version="8.8.2",
        labware=[
            _labware(PLATE_ID, NAMES_96, PCR),
            _labware(RACK_ID, tubes, TUBE),
            _labware(TIPS_ID, NAMES_96, WellGeometry(59.3, 300, "circular", 5.23)),
            _labware(FLAT_ID, NAMES_96, FLAT, module="temperatureModuleV2"),
            _labware(TROUGH_ID, [f"A{col}" for col in range(1, 13)], TROUGH),
        ],
        pipettes=[
            Pipette("right", "p300_single_gen2", 1, 20, 300),
            Pipette("left", "p300_multi_gen2", 8, 20, 300),
        ],
        liquid_loads=[
            LiquidLoad(well, name, None, volume, None) for well, (name, volume) in loads.items()
        ],
    )


Keys = WellKey | Sequence[WellKey]


def _list(keys: Keys) -> list[WellKey]:
    return [keys] if isinstance(keys, WellKey) else list(keys)


class TraceBuilder:
    """Appends events; each takes one second unless it is a delay. One tip or a list of tips:
    a list is a multi-channel action, tip i in well i."""

    def __init__(self, loads: Mapping[WellKey, tuple[str, float]] | None = None) -> None:
        self.deck = deck(loads or {})
        self.events: list[Event] = []
        self.clock = 0.0

    def _event(
        self,
        op: Op,
        targets: list[Target],
        *,
        volume: float | None = None,
        height: float | None = None,
        parent: str | None = None,
        duration: float | None = None,
        celsius: float | None = None,
        labware_id: str | None = None,
        returned: bool = False,
    ) -> int:
        index = len(self.events)
        self.events.append(
            Event(
                index=index,
                op=op,
                line=index + 1,
                stack=[f"run:{index + 1}"],
                parent=parent,
                mount="left" if len(targets) > 1 else "right",
                targets=targets,
                volume_ul=volume,
                height_mm=height,
                t_est_s=self.clock,
                duration_s=duration,
                celsius=celsius,
                module=None,
                labware_id=labware_id,
                returned=returned,
            )
        )
        self.clock += duration if duration is not None else 1.0
        return index

    @staticmethod
    def _targets(tips: Keys | None, wells: Keys) -> list[Target]:
        well_list = _list(wells)
        tip_list = [None] * len(well_list) if tips is None else _list(tips)
        return [Target(tip=t, well=w) for t, w in zip(tip_list, well_list, strict=True)]

    def pick_up(self, tips: Keys) -> int:
        return self._event("pick_up_tip", self._targets(tips, tips))

    def drop(self, tips: Keys, returned: bool = False) -> int:
        return self._event("drop_tip", self._targets(tips, tips), returned=returned)

    def aspirate(
        self,
        tips: Keys | None,
        wells: Keys,
        volume: float | None,
        height: float | None = LOW,
        parent: str | None = None,
    ) -> int:
        targets = self._targets(tips, wells)
        return self._event("aspirate", targets, volume=volume, height=height, parent=parent)

    def dispense(
        self,
        tips: Keys | None,
        wells: Keys,
        volume: float | None,
        height: float | None = LOW,
        parent: str | None = None,
    ) -> int:
        targets = self._targets(tips, wells)
        return self._event("dispense", targets, volume=volume, height=height, parent=parent)

    def blow_out(self, tips: Keys, wells: Keys, height: float | None = ABOVE) -> int:
        return self._event("blow_out", self._targets(tips, wells), height=height)

    def touch_tip(self, tips: Keys, wells: Keys, height: float | None = 9.0) -> int:
        return self._event("touch_tip", self._targets(tips, wells), height=height)

    def delay(self, seconds: float) -> int:
        return self._event("delay", [], duration=seconds)

    def set_temperature(self, labware_id: str, celsius: float) -> int:
        return self._event("set_temperature", [], celsius=celsius, labware_id=labware_id)

    def deactivate(self, labware_id: str) -> int:
        return self._event("deactivate", [], labware_id=labware_id)

    def other(self, op: Op) -> int:
        return self._event(op, [])

    def trace(self) -> Trace:
        return Trace(deck=self.deck, events=list(self.events))
