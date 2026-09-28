# WHAT THIS TESTS (should FIRE)
# A PCR setup that uses a p300 to add 5 ul of sample to each reaction. The p300 cannot measure
# less than 20 ul; the simulator passes it and every volume adds up on paper. A Nemotron draft
# in eval/agent did exactly this and was "verified".
from opentrons import protocol_api

metadata = {"protocolName": "p300 draws 5 ul", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    mix = protocol.define_liquid("master mix", "PCR master mix", "#1f77b4")
    tubes["A1"].load_liquid(mix, 500)
    samples = [tubes[f"B{i}"] for i in range(1, 5)]
    for i, tube in enumerate(samples):
        tube.load_liquid(protocol.define_liquid(f"sample {i + 1}", "DNA", "#ff7f0e"), 50)

    p300.pick_up_tip()
    for i in range(4):
        p300.aspirate(20, tubes["A1"])
        p300.dispense(20, plate.wells()[i].top())
    p300.drop_tip()
    for i, tube in enumerate(samples):
        p300.pick_up_tip()
        p300.aspirate(5, tube)  # below the p300's 20 ul minimum
        p300.dispense(5, plate.wells()[i])
        p300.drop_tip()
