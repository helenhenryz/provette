# WHAT THIS TESTS (should NOT fire)
# Eight spent samples of 300 ul emptied into one 1.5 ml tube in a rack labelled "waste", well
# past what the tube holds. Waste is meant to be filled; the rule leaves it alone.
from opentrons import protocol_api

metadata = {"protocolName": "waste over its maximum", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    waste = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "waste")
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    spent = protocol.define_liquid("spent medium", "spent medium", "#7f7f7f")
    for n in range(1, 9):
        plate[f"A{n}"].load_liquid(spent, 1000)
    for n in range(1, 9):
        p300.transfer(300, plate[f"A{n}"], waste["A1"], new_tip="always")
