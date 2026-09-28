# WHAT THIS TESTS (should NOT fire)
# Three technical replicates of the SAME sample. The dye reagent goes into three empty wells
# with one tip, the sample is added to the three wells from above with one other tip, and then
# a third tip mixes replicate 1, replicate 2 and replicate 3 in turn. That tip goes from well to
# well while wet: but all three wells hold exactly the same two liquids, so nothing arrives
# anywhere that was not put there on purpose.
# New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Three replicates mixed with one tip"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    sample = protocol.define_liquid("serum sample", "one patient", "#AA0000")
    reagent = protocol.define_liquid("Bradford reagent", "dye", "#0000AA")
    rack["A1"].load_liquid(sample, 500)
    rack["B1"].load_liquid(reagent, 1200)

    replicates = [plate["A1"], plate["A2"], plate["A3"]]
    p300.transfer(100, rack["B1"], replicates, new_tip="once")
    p300.transfer(50, rack["A1"], [well.top() for well in replicates], new_tip="once")
    p300.pick_up_tip()
    for well in replicates:
        p300.mix(3, 80, well)
    p300.drop_tip()
