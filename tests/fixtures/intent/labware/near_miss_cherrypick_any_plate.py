# WHAT THIS TESTS (should NOT fire)
# Cherry-picking: 10 ul from 4 named wells of a source plate into a flat plate. The technique
# needs no particular kind of plate, so the check says nothing whatever the destination is.
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    source = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "source")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, "picked")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    picks = ["B3", "D7", "F2", "H11"]
    for well in picks:
        liquid = protocol.define_liquid(f"clone {well}", "culture", "#0a0")
        source[well].load_liquid(liquid, 50)

    for well, dest in zip(picks, ["A1", "B1", "C1", "D1"]):
        p20.pick_up_tip()
        p20.aspirate(10, source[well])
        p20.dispense(10, plate[dest])
        p20.drop_tip()
