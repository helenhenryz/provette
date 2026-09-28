# WHAT THIS TESTS (should NOT fire)
# Four wells of water get four samples with ONE tip: the tip carries sample 1 into wells 2
# to 4. That is a real mix-up (CONTAM-WELL's), but the wells hold water, not a reagent, so
# this rule, which is about reagent wells, stays silent.
from opentrons import protocol_api

metadata = {"protocolName": "samples into water wells with one tip", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    water = protocol.define_liquid("nuclease-free water", "molecular biology grade", "#1f77b4")
    tubes["A1"].load_liquid(water, 1000)
    samples = [
        protocol.define_liquid(f"sample {n}", f"genomic DNA of sample {n}", "#d62728")
        for n in range(1, 5)
    ]
    sample_tubes = [tubes[f"B{n}"] for n in range(1, 5)]
    for tube, sample in zip(sample_tubes, samples, strict=True):
        tube.load_liquid(sample, 50)

    wells = [plate[f"A{n}"] for n in range(1, 5)]
    p20.transfer(15, tubes["A1"], wells, new_tip="once")
    p20.transfer(5, sample_tubes, wells, new_tip="once")  # one tip, into the water each time
