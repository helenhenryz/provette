# WHAT THIS TESTS (should FIRE)
# 2 ml of PCR master mix declared in a 195 ml one-well reservoir, and 96 draws of 18 ul at the
# default height, 1 mm above the bottom. The reservoir floor is 107 by 71 mm with a grid of
# dimples, and 2 ml stands only 1.2 mm deep: after 46 draws the surface is below the tip and the
# remaining 50 draws are air. The simulator passes every step. This is the shape of Super's
# verified pcr-03 draft in eval/agent.
from opentrons import protocol_api

metadata = {"protocolName": "master mix from a 195 ml reservoir", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = [protocol.load_labware("opentrons_96_tiprack_20ul", slot) for slot in (1, 2)]
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=tips)

    master_mix = protocol.define_liquid("master mix", "PCR master mix", "#1f77b4")
    reservoir["A1"].load_liquid(master_mix, 2000)  # 96 x 18 = 1728 ul, plus some overage

    for well in pcr_plate.wells():
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"])
        p20.dispense(18, well)
        p20.drop_tip()
