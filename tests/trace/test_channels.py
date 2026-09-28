"""The multi-channel rule (DECISIONS.md D-11), tested straight on Opentrons' labware definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import opentrons_shared_data

from provette.trace._channels import channel_wells, full_offsets

DEFINITIONS = Path(opentrons_shared_data.__file__).parent / "data" / "labware" / "definitions" / "2"
EIGHT = full_offsets(8)


def definition(load_name: str) -> dict[str, Any]:
    newest = max((DEFINITIONS / load_name).glob("*.json"), key=lambda p: int(p.stem))
    loaded: dict[str, Any] = json.loads(newest.read_text(encoding="utf-8"))
    return loaded


def test_single_channel_is_the_named_well() -> None:
    plate = definition("nest_96_wellplate_200ul_flat")
    assert channel_wells(plate, "C7", full_offsets(1)) == ["C7"]


def test_96_well_plate_is_the_whole_column() -> None:
    plate = definition("nest_96_wellplate_200ul_flat")
    assert channel_wells(plate, "A3", EIGHT) == [f"{row}3" for row in "ABCDEFGH"]


def test_384_well_plate_is_every_other_row() -> None:
    plate = definition("corning_384_wellplate_112ul_flat")
    assert channel_wells(plate, "A1", EIGHT) == [f"{row}1" for row in "ACEGIKMO"]
    assert channel_wells(plate, "B2", EIGHT) == [f"{row}2" for row in "BDFHJLNP"]


def test_reservoir_takes_all_eight_tips_in_one_well() -> None:
    reservoir = definition("nest_12_reservoir_15ml")
    assert channel_wells(reservoir, "A4", EIGHT) == ["A4"] * 8


def test_single_well_reservoir() -> None:
    reservoir = definition("agilent_1_reservoir_290ml")
    assert channel_wells(reservoir, "A1", EIGHT) == ["A1"] * 8


def test_tip_rack_column() -> None:
    rack = definition("opentrons_96_tiprack_300ul")
    assert channel_wells(rack, "A12", EIGHT) == [f"{row}12" for row in "ABCDEFGH"]


def test_channels_hanging_off_the_plate_enter_nothing() -> None:
    plate = definition("nest_96_wellplate_200ul_flat")
    assert channel_wells(plate, "E1", EIGHT) == ["E1", "F1", "G1", "H1", None, None, None, None]


def test_tube_rack_tips_land_between_tubes() -> None:
    # Tubes are 19.3 mm apart and tips 9 mm apart: nobody should do this, but if a protocol
    # does, only the channels that are over a tube are reported.
    rack = definition("opentrons_24_tuberack_nest_1.5ml_snapcap")
    wells = channel_wells(rack, "A1", EIGHT)
    assert wells[0] == "A1" and wells[1] is None and wells[2] == "B1"
