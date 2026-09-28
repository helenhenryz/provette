# WHAT THIS TESTS (should FIRE)
# 500 ul of enzyme mix in one channel of a 12-channel 15 ml reservoir, drawn 96 times at the
# default 1 mm. The channel is 71 mm long: 500 ul stands 1.7 mm deep, so the first 62 draws of
# 5 ul are in the liquid; at 190 ul the surface is under the tip and the other 34 draws are
# air. The 190 ul never leave the channel: a reservoir's dead volume, seen from the tip.
from opentrons import protocol_api

metadata = {"protocolName": "enzyme from a 15 ml channel", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = [protocol.load_labware("opentrons_96_tiprack_20ul", slot) for slot in (1, 2)]
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=tips)

    enzyme = protocol.define_liquid("enzyme mix", "restriction enzyme in buffer", "#2ca02c")
    reservoir["A1"].load_liquid(enzyme, 500)

    for well in plate.wells():
        p20.pick_up_tip()
        p20.aspirate(5, reservoir["A1"])
        p20.dispense(5, well)
        p20.drop_tip()
