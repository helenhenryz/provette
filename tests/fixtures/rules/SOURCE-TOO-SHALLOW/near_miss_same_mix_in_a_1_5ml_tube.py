# WHAT THIS TESTS (should NOT fire)
# The same master mix drawn from a 1.5 ml snap-cap tube instead of a reservoir: 1 ml declared,
# 48 draws of 18 ul at the default 1 mm. The tube is conical, and the definition's shape says
# the 136 ul left at the end still stand 8 mm deep. The tip never leaves the liquid. (The
# catalogue expected this to stay uncertain; with the shape in the trace it is known and dry
# nowhere.)
from opentrons import protocol_api

metadata = {"protocolName": "master mix from a 1.5 ml tube", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    master_mix = protocol.define_liquid("master mix", "PCR master mix", "#1f77b4")
    tubes["A1"].load_liquid(master_mix, 1000)  # 48 x 18 = 864 ul, plus some overage

    for well in pcr_plate.wells()[:48]:
        p20.pick_up_tip()
        p20.aspirate(18, tubes["A1"])
        p20.dispense(18, well)
        p20.drop_tip()
