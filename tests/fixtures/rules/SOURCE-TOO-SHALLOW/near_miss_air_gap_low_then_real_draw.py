# WHAT THIS TESTS (should NOT fire)
# An air gap written by hand, low in the well. 300 ul of buffer in one channel of a 12-channel
# reservoir stands about 1 mm deep. The author aspirates 20 ul at well.bottom(5), above the
# liquid, and then, with the same tip and nothing in between, 100 ul at well.bottom(1), in the
# liquid. The first draw is an air gap, not a shallow source: 5 mm is in the bottom half of the
# channel, so the top-half exclusion does not cover it; the real draw straight after does. This
# is the shape of the one false alarm in the flood read over the public library.
from opentrons import protocol_api

metadata = {"protocolName": "air gap low then the real draw", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    buffer = protocol.define_liquid("buffer", "elution buffer", "#7f7f7f")
    reservoir["A1"].load_liquid(buffer, 300)

    p300.pick_up_tip()
    p300.aspirate(20, reservoir["A1"].bottom(5))  # an air gap by hand, above the liquid
    p300.aspirate(100, reservoir["A1"].bottom(1))  # the real draw, in the liquid
    p300.dispense(120, plate["A1"].top())
    p300.drop_tip()
