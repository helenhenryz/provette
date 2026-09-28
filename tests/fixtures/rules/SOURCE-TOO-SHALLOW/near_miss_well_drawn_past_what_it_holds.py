# WHAT THIS TESTS (should NOT fire)
# 100 ul of primer declared in one channel of a 12-channel reservoir, and one draw of 100 ul at
# the default 1 mm. 100 ul stands well under 1 mm deep in that channel, so the tip is above
# the liquid and the draw is air: but the well holds exactly what the draw asks for, no more,
# and the prep sheet already says so ("no margin": 100 ul needed, 100 ul declared). The well is
# short, not shallow, and this rule leaves it to the prep sheet. (Two library tubes declared at
# exactly what the run needs were reported this way before the exclusion read "no more than".
# A tube cannot make this case: every tube in the library lifts 100 ul above the 1 mm tip, so
# the draw there is short liquid, not air.)
from opentrons import protocol_api

metadata = {"protocolName": "well drawn past what it holds", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    primer = protocol.define_liquid("primer", "forward primer, 10 uM", "#ff7f0e")
    reservoir["A1"].load_liquid(primer, 100)

    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["A1"].top())
    p300.drop_tip()
