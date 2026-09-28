# WHAT THIS TESTS (should FIRE, as a warning)
# A ten-fold serial dilution of a standard for a qPCR standard curve, with a fresh tip at every
# step, which is good: but the author forgot to mix. 20 uL of standard is dropped into 180 uL of
# water and the next 20 uL is drawn straight out again. The drawn liquid is not a ten-fold
# dilution of anything, and every later step inherits the error.
# New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Standard curve: ten-fold dilutions, never mixed"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    standard = protocol.define_liquid("DNA standard", "10^8 copies per uL", "#AA0000")
    water = protocol.define_liquid("water", "nuclease-free water", "#0000FF")
    rack["A1"].load_liquid(standard, 500)
    rack["B1"].load_liquid(water, 1400)

    steps = [plate[f"A{n}"] for n in range(1, 7)]
    p300.transfer(180, rack["B1"], steps, new_tip="once")
    p300.transfer(20, rack["A1"], steps[0], new_tip="always")
    p300.transfer(20, steps[:-1], steps[1:], new_tip="always")  # no mix_after
