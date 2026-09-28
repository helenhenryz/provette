# WHAT THIS TESTS (should NOT fire)
# A 2 ml deep-well plate filled to 1.9 ml of medium with no mixing: under the maximum, and no
# stroke to push it over.
from opentrons import protocol_api

metadata = {"protocolName": "deep well nearly full", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips])

    medium = protocol.define_liquid("LB", "medium", "#8c564b")
    reservoir["A1"].load_liquid(medium, 100000)
    p1000.transfer(1900, reservoir["A1"], [plate[f"A{n}"] for n in range(1, 5)], new_tip="once")
