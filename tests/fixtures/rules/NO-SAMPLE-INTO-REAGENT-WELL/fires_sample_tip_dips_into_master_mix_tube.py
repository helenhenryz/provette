# WHAT THIS TESTS (should FIRE, as a note while the rule is proposed)
# The author puts the sample into the PCR well first and then, with the SAME tip, goes to
# the master mix tube for the mix. The tip has been in the sample, and the tube holds a
# reagent, so the shared mix now carries sample 1. Also CONTAM-STOCK's case; here the rule
# fires because the well the tip enters holds a reagent.
from opentrons import protocol_api

metadata = {"protocolName": "sample tip into the master mix tube", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    mix = protocol.define_liquid("PCR master mix", "2x master mix with polymerase", "#2ca02c")
    sample = protocol.define_liquid("sample 1", "genomic DNA of sample 1", "#d62728")
    tubes["A1"].load_liquid(mix, 500)
    tubes["B1"].load_liquid(sample, 50)

    p20.pick_up_tip()
    p20.aspirate(5, tubes["B1"])
    p20.dispense(5, plate["A1"])
    p20.aspirate(15, tubes["A1"])  # the same tip, wet with sample, into the mix
    p20.dispense(15, plate["A1"])
    p20.drop_tip()
