# WHAT THIS TESTS (should FIRE)
# Twelve PCRs assembled from master mix, primers and templates held in an aluminium block on a
# temperature module that the protocol loads and never sets. The block stays at room
# temperature for the whole run; the person at the bench sees a module and assumes it is cold.
# One warning, anchored at the first draw from the block, naming the liquids on it.
from opentrons import protocol_api

metadata = {"protocolName": "PCR from a module never set", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    temp_module = protocol.load_module("temperature module gen2", 3)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "reagents")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    master_mix = protocol.define_liquid("Q5 master mix", "2x hot-start polymerase mix", "#1f77b4")
    primers = protocol.define_liquid("primer mix", "forward and reverse, 10 uM each", "#2ca02c")
    template = protocol.define_liquid("DNA template", "genomic DNA, 5 ng/ul", "#d62728")
    block["A1"].load_liquid(master_mix, 400)
    block["A2"].load_liquid(primers, 100)
    templates = [well for column in block.columns()[2:5] for well in column]  # 12 tubes
    for tube in templates:
        tube.load_liquid(template, 50)

    reactions = [plate[f"A{n}"] for n in range(1, 13)]
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(12.5, block["A1"])
        p20.dispense(12.5, well)
    p20.drop_tip()
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(2.5, block["A2"])
        p20.dispense(2.5, well)
    p20.drop_tip()
    for tube, well in zip(templates, reactions):
        p20.pick_up_tip()
        p20.aspirate(5, tube)
        p20.dispense(5, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
