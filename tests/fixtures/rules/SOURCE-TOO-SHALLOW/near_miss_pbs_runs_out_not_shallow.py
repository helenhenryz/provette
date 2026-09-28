# WHAT THIS TESTS (should NOT fire)
# 1.2 ml of PBS in one channel of a 12-channel reservoir and 12 draws of 100 ul at the default
# 1 mm. The first eleven draws are in the liquid. The twelfth finds 100 ul left, 0.55 mm deep,
# and draws air: but the well is running out, not shallow. That is the prep sheet's flag (it
# needs all 1.2 ml, with no margin), and this rule leaves it alone.
from opentrons import protocol_api

metadata = {"protocolName": "PBS runs out", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "phosphate-buffered saline", "#7f7f7f")
    reservoir["A1"].load_liquid(pbs, 1200)

    p300.pick_up_tip()
    for well in plate.wells()[:12]:
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, well.top())
    p300.drop_tip()
