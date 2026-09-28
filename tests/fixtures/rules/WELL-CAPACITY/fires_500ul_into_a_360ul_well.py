# WHAT THIS TESTS (should FIRE, as an error)
# 500 ul of medium into each well of a Corning 360 ul plate, which holds 366 ul to its rim by
# the labware definition's shape. The liquid runs over into the neighbours and onto the deck.
# Two protocols in the public library do exactly this.
from opentrons import protocol_api

metadata = {"protocolName": "500 ul into a 360 ul well", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    medium = protocol.define_liquid("medium", "growth medium", "#8c564b")
    reservoir["A1"].load_liquid(medium, 10000)
    p300.transfer(500, reservoir["A1"], [plate[f"A{n}"] for n in range(1, 5)], new_tip="once")
