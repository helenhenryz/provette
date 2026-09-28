# WHAT THIS TESTS (should FIRE)
# Eight 25 ul PCRs assembled as 5x buffer, polymerase, primers, water, template: the polymerase
# goes into 5 ul of neat 5x buffer, and the 15 ul of water that makes the reaction only comes
# after the primers. This is the pcr-07 shape from eval/agent. One finding on the polymerase's
# line, eight occurrences.
from opentrons import protocol_api

metadata = {"protocolName": "PCR: buffer, polymerase, primers, water, template", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    water = protocol.define_liquid("nuclease-free water", "molecular biology grade", "#1f77b4")
    buffer = protocol.define_liquid("5x Q5 buffer", "5x reaction buffer", "#ff7f0e")
    polymerase = protocol.define_liquid("Q5 polymerase", "high-fidelity DNA polymerase", "#2ca02c")
    fwd = protocol.define_liquid("forward primer", "10 uM", "#9467bd")
    rev = protocol.define_liquid("reverse primer", "10 uM", "#8c564b")
    templates = [
        protocol.define_liquid(f"template {n}", f"genomic DNA {n}", "#d62728") for n in range(1, 9)
    ]
    tubes["A1"].load_liquid(water, 1000)
    tubes["A2"].load_liquid(buffer, 200)
    tubes["A3"].load_liquid(polymerase, 50)
    tubes["A4"].load_liquid(fwd, 100)
    tubes["A5"].load_liquid(rev, 100)
    template_tubes = [tubes[f"B{col}"] for col in range(1, 7)] + [tubes["C1"], tubes["C2"]]
    for tube, template in zip(template_tubes, templates, strict=True):
        tube.load_liquid(template, 100)

    for n, template_tube in enumerate(template_tubes, start=1):
        reaction = plate[f"A{n}"]
        p20.transfer(5, tubes["A2"], reaction)  # 5x buffer
        p20.transfer(1, tubes["A3"], reaction)  # polymerase, into neat buffer
        p20.transfer(1, tubes["A4"], reaction)
        p20.transfer(1, tubes["A5"], reaction)
        p20.transfer(15, tubes["A1"], reaction)  # the water comes after the polymerase
        p20.transfer(2, template_tube, reaction)
