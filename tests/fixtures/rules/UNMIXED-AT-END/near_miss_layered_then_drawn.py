# WHAT THIS TESTS (should NOT fire)
# A sample is diluted in a tube (10 ul of serum into 90 ul of buffer, no mix) and the dilution
# is then plated: 20 ul drawn from the tube into each of four empty wells. The tube is layered
# and unmixed, but the protocol draws from it afterwards, and that is MIX-BEFORE-DRAW's finding,
# not this rule's. The plate wells were empty when the dilution landed, so they are not layered.
from opentrons import protocol_api

metadata = {"protocolName": "Dilute in a tube, then plate", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    buffer = protocol.define_liquid("assay buffer", "1x", "#1f77b4")
    serum = protocol.define_liquid("serum sample", "patient 1", "#ff7f0e")
    reservoir["A1"].load_liquid(buffer, 5000)
    tubes["A1"].load_liquid(serum, 100)

    dilution = tubes["B1"]
    p300.transfer(90, reservoir["A1"], dilution, new_tip="always")
    p20.transfer(10, tubes["A1"], dilution, new_tip="always")
    p300.transfer(20, dilution, plate.columns()[0][:4], new_tip="once")
