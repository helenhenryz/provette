# WHAT THIS TESTS (should NOT fire)
# A temperature module carries a block of spare tubes that the protocol never pipettes from or
# into; the PCRs are built from a tube rack on the deck. The module is never set, but nothing on
# it is used, so there is nothing to keep cold and nothing to report.
from opentrons import protocol_api

metadata = {"protocolName": "module with a spare block", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    temp_module = protocol.load_module("temperature module gen2", 3)
    spare = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "spare")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "reagents")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    master_mix = protocol.define_liquid("Q5 master mix", "2x hot-start polymerase mix", "#1f77b4")
    template = protocol.define_liquid("DNA template", "genomic DNA, 5 ng/ul", "#d62728")
    water = protocol.define_liquid("water", "nuclease free", "#1f77b4")
    rack["A1"].load_liquid(master_mix, 400)
    rack["A2"].load_liquid(template, 50)
    spare["A1"].load_liquid(water, 1000)

    reactions = [plate[f"A{n}"] for n in range(1, 9)]
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(12.5, rack["A1"])
        p20.dispense(12.5, well)
    p20.drop_tip()
    for well in reactions:
        p20.pick_up_tip()
        p20.aspirate(5, rack["A2"])
        p20.dispense(5, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
