# WHAT THIS TESTS (should NOT fire)
# A p300 transfer with a 10 ul air gap. The air gap is an aspirate of 10 ul, below the p300's
# 20 ul minimum, but it is air, not liquid, and must not be judged.
from opentrons import protocol_api

metadata = {"protocolName": "air gap below minimum", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    p300.transfer(100, reservoir["A1"], plate.wells()[:8], air_gap=10, new_tip="once")
