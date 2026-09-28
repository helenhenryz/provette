# WHAT THIS TESTS (should FIRE)
# A p1000 is used to mix 50 ul in a well. A mix is an aspirate like any other, and 50 ul is below
# the p1000's 100 ul minimum. Old API level, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "p1000 mixes 50 ul", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips])

    p1000.pick_up_tip()
    for well in plate.wells()[:8]:
        p1000.aspirate(500, reservoir["A1"])
        p1000.dispense(500, well)
        p1000.mix(3, 50, well)  # 50 ul is below the p1000's minimum
    p1000.drop_tip()
