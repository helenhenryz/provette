"""The three "complex commands": transfer, distribute and consolidate.

Each one is a single line in the protocol, and the robot turns it into many small steps:
pick up a tip, aspirate, take an air gap, dispense, mix, blow out, drop the tip.
Provette records the small steps and remembers which big command each one came from.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Transfer, distribute, consolidate"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    dye = protocol.define_liquid("dye", description="blue dye", display_color="#0000FF")
    rack["A1"].load_liquid(dye, 1200)

    # One source to two wells, a fresh tip each time, a bubble of air behind the liquid so it
    # does not drip, and three mixes after each dispense.
    p300.transfer(
        50, rack["A1"], [plate["A1"], plate["A2"]], new_tip="always", air_gap=20, mix_after=(3, 30)
    )

    # One aspirate, several dispenses; what is left over is blown out back into the source.
    p300.distribute(
        30, rack["A1"], [plate["B1"], plate["B2"], plate["B3"]], blow_out=True, blowout_location="source well"
    )

    # Several aspirates, one dispense.
    p300.consolidate(40, [plate["B1"], plate["B2"]], rack["A2"], air_gap=10)
