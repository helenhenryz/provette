# WHAT THIS TESTS (should FIRE, as a note)
# A qPCR plate: six cDNA samples in triplicate, 15 ul of SYBR master mix and 5 ul of cDNA in
# each of 18 wells, and nothing else on the plate. No well holds the mix without a sample, so
# there is no no-template control: a contaminated reagent or a primer-dimer would light up
# every well and nothing could tell. This is the shape of the E5 pcr-04 drafts.
from opentrons import protocol_api

metadata = {"protocolName": "qPCR, six cDNAs in triplicate, no NTC", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("SYBR master mix", "2x SYBR green qPCR master mix", "#2ca02c")
    tubes["A1"].load_liquid(mix, 400)
    samples = []
    for n in range(1, 7):
        cdna = protocol.define_liquid(f"cDNA sample {n}", f"cDNA from sample {n}", "#d62728")
        tubes[f"B{n}"].load_liquid(cdna, 30)
        samples.append(tubes[f"B{n}"])

    rows = ["A", "B", "C"]
    reactions = [[plate[f"{row}{n}"] for row in rows] for n in range(1, 7)]

    p20.pick_up_tip()
    for triplicate in reactions:
        for well in triplicate:
            p20.aspirate(15, tubes["A1"])
            p20.dispense(15, well)
    p20.drop_tip()

    for source, triplicate in zip(samples, reactions):
        p20.pick_up_tip()
        p20.aspirate(15, source)
        for well in triplicate:
            p20.dispense(5, well)
        for well in triplicate:
            p20.mix(3, 10, well)
        p20.drop_tip()
