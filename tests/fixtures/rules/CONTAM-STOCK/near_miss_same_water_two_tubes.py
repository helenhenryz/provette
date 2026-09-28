# WHAT THIS TESTS (should NOT fire)
# Water is kept in two tubes because one tube is not enough. One tip draws from the first tube,
# fills some wells, and then draws from the second tube. The tip does carry "another tube's
# liquid" into the second tube: but both were declared as the same liquid, nuclease-free water,
# and water from two tubes is still water. New API (2.20), single-channel, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Water from two tubes with one tip"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    water = protocol.define_liquid("nuclease-free water", "water", "#0000FF")
    rack["A1"].load_liquid(water, 1000)
    rack["A2"].load_liquid(water, 1000)

    p300.pick_up_tip()
    for name in ["A1", "A2", "A3", "A4"]:
        p300.aspirate(50, rack["A1"])
        p300.dispense(50, plate[name])
    for name in ["A5", "A6", "A7", "A8"]:
        p300.aspirate(50, rack["A2"])
        p300.dispense(50, plate[name])
    p300.drop_tip()
