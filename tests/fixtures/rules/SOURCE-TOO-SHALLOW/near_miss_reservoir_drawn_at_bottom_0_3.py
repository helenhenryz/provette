# WHAT THIS TESTS (should NOT fire)
# The same 2 ml of master mix in the same 195 ml reservoir, 96 draws of 18 ul, but the author
# aspirates at well.bottom(0.3) instead of the default 1 mm. Even the last draw, with 290 ul
# left standing 0.4 mm deep, has the tip in the liquid.
from opentrons import protocol_api

metadata = {"protocolName": "master mix drawn low from a 195 ml reservoir", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = [protocol.load_labware("opentrons_96_tiprack_20ul", slot) for slot in (1, 2)]
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=tips)

    master_mix = protocol.define_liquid("master mix", "PCR master mix", "#1f77b4")
    reservoir["A1"].load_liquid(master_mix, 2000)

    for well in pcr_plate.wells():
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"].bottom(0.3))
        p20.dispense(18, well)
        p20.drop_tip()
