# WHAT THIS TESTS (should NOT fire)
# The same PCR setup as fires_p300_draws_5ul.py, written properly: the 5 ul of sample is drawn
# with a p20, whose range is 1 to 20 ul. The 20 ul of master mix is drawn with the p300, which is
# exactly its minimum, so that is fine too.
from opentrons import protocol_api

metadata = {"protocolName": "p20 draws 5 ul", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

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
        p20.pick_up_tip()
        p20.aspirate(5, tube)
        p20.dispense(5, plate.wells()[i])
        p20.drop_tip()
