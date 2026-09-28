# WHAT THIS TESTS (should FIRE)
# Twelve 20 ul restriction digests assembled in the order buffer, enzyme, plasmid, water: the
# enzyme goes into 2 ul of neat 10x buffer and the water only comes last. Every clone-01 draft
# in eval/agent did exactly this. One finding, on the enzyme's transfer line, with 12 occurrences
# and the water named as what came after.
from opentrons import protocol_api

metadata = {"protocolName": "digests: buffer, enzyme, plasmid, water", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

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

    for n, plasmid_tube in enumerate(plasmid_tubes, start=1):
        digest = plate[f"A{n}"]
        p20.transfer(2, tubes["A2"], digest)  # 10x buffer
        p20.transfer(1, tubes["A3"], digest)  # enzyme, into neat buffer
        p20.transfer(5, plasmid_tube, digest)
        p20.transfer(12, tubes["A1"], digest)  # the water comes last
