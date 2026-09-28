# WHAT THIS TESTS (should FIRE, as a note while the rule is proposed)
# Master mix is handed out to four PCR wells, the four samples go in with a fresh tip each,
# and then the author mixes all four reactions with ONE tip: it stirs well 1 with sample 1 on
# it, then well 2, and so on. Sample 1 rides into wells 2 to 4, which hold master mix (a
# reagent). CONTAM-WELL sees the same touches; this rule names the reagent wells. One
# finding, on the mixing line, titled "(proposed) ..." because the rule is not adopted yet.
from opentrons import protocol_api

metadata = {"protocolName": "reactions mixed with one tip", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    mix = protocol.define_liquid("PCR master mix", "2x master mix with polymerase", "#2ca02c")
    tubes["A1"].load_liquid(mix, 500)
    samples = [
        protocol.define_liquid(f"sample {n}", f"genomic DNA of sample {n}", "#d62728")
        for n in range(1, 5)
    ]
    sample_tubes = [tubes[f"B{n}"] for n in range(1, 5)]
    for tube, sample in zip(sample_tubes, samples, strict=True):
        tube.load_liquid(sample, 50)

    wells = [plate[f"A{n}"] for n in range(1, 5)]
    p20.transfer(15, tubes["A1"], wells, new_tip="once")  # mix first, one clean tip
    p20.transfer(5, sample_tubes, wells, new_tip="always")  # samples, a fresh tip each
    p20.pick_up_tip()
    for well in wells:
        p20.mix(3, 10, well)  # ONE tip stirs every reaction
    p20.drop_tip()
