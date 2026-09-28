# WHAT THIS TESTS (should NOT fire)
# The right way to do twelve digests: water, buffer and enzyme go into one tube (in that order,
# and mixed), and 15 ul of that master mix is handed out to twelve wells, each then getting its
# plasmid. The enzyme reaches the plate inside the mix, not from its own stock, and nothing
# comes after it in the tube. No finding.
from opentrons import protocol_api

metadata = {"protocolName": "digests from a master mix", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])

    water = protocol.define_liquid("nuclease-free water", "molecular biology grade", "#1f77b4")
    buffer = protocol.define_liquid("10x buffer", "10x restriction buffer", "#ff7f0e")
    enzyme = protocol.define_liquid("BsaI enzyme", "restriction enzyme in 50% glycerol", "#2ca02c")
    plasmids = [
        protocol.define_liquid(f"plasmid {n}", f"miniprep of plasmid {n}", "#d62728")
        for n in range(1, 13)
    ]
    tubes["A1"].load_liquid(water, 1000)
    tubes["A2"].load_liquid(buffer, 200)
    tubes["A3"].load_liquid(enzyme, 50)
    plasmid_tubes = [tubes[f"{row}{col}"] for row in "BCD" for col in range(1, 5)]
    for tube, plasmid in zip(plasmid_tubes, plasmids, strict=True):
        tube.load_liquid(plasmid, 100)

    mix = tubes["A4"]  # empty: the master mix for 13 digests is built here
    p300.transfer(156, tubes["A1"], mix)  # water
    p300.transfer(26, tubes["A2"], mix)  # 10x buffer
    p20.transfer(13, tubes["A3"], mix)  # enzyme last
    p300.pick_up_tip()
    p300.mix(5, 150, mix)
    p300.drop_tip()

    digests = [plate[f"A{n}"] for n in range(1, 13)]
    p20.transfer(15, mix, digests, new_tip="always")
    for plasmid_tube, digest in zip(plasmid_tubes, digests, strict=True):
        p20.transfer(5, plasmid_tube, digest)
