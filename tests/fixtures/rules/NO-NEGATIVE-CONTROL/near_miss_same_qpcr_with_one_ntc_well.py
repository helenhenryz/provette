# WHAT THIS TESTS (should NOT fire)
# The same qPCR plate (six cDNAs in triplicate, 15 ul of SYBR master mix and 5 ul of cDNA),
# plus one well of mix and 5 ul of water in place of the template. That well is the
# no-template control, so the plate has what MIQE asks for and the rule is silent.
from opentrons import protocol_api

metadata = {"protocolName": "qPCR, six cDNAs in triplicate, one NTC", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("SYBR master mix", "2x SYBR green qPCR master mix", "#2ca02c")
    water = protocol.define_liquid("water", "nuclease-free water", "#1f77b4")
    tubes["A1"].load_liquid(mix, 400)
    tubes["D6"].load_liquid(water, 500)
    samples = []
    for n in range(1, 7):
        cdna = protocol.define_liquid(f"cDNA sample {n}", f"cDNA from sample {n}", "#d62728")
        tubes[f"B{n}"].load_liquid(cdna, 30)
        samples.append(tubes[f"B{n}"])

    rows = ["A", "B", "C"]
    reactions = [[plate[f"{row}{n}"] for row in rows] for n in range(1, 7)]
    ntc = plate["D1"]

    p20.pick_up_tip()
    for well in [w for triplicate in reactions for w in triplicate] + [ntc]:
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

    p20.pick_up_tip()
    p20.aspirate(5, tubes["D6"])
    p20.dispense(5, ntc)
    p20.mix(3, 10, ntc)
    p20.drop_tip()
