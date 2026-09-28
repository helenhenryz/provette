import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "qPCR setup 6 samples triplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 3)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    strip_block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)

    # liquids
    master_mix = protocol.define_liquid(name="master mix", description="SYBR master mix with primers", display_color="#FF0000")
    sample1 = protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    sample2 = protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    sample3 = protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    sample4 = protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    sample5 = protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    sample6 = protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#808080")

    # initial volumes
    tuberack["A1"].load_liquid(liquid=master_mix, volume=500)  # master mix tube
    strip_wells = [strip_block["A1"], strip_block["B1"], strip_block["C1"], strip_block["D1"], strip_block["E1"], strip_block["F1"]]
    samples_liquids = [sample1, sample2, sample3, sample4, sample5, sample6]
    for well, liq in zip(strip_wells, samples_liquids):
        well.load_liquid(liquid=liq, volume=100)  # each sample ~100 ul

    # instruments
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])

    # set temperature block to 4°C
    temp_mod.set_temperature(4)
    # destination wells (first 18)
    dest_wells = plate.wells()[:18]

    # distribute master mix: 8 ul each
    p300.pick_up_tip()
    total_mm = 8 * len(dest_wells)
    p300.aspirate(total_mm, tuberack["A1"])
    for well in dest_wells:
        p300.dispense(8, well)
    p300.drop_tip()

    # distribute samples: 2 ul each to triplicates, mix after addition
    for i, samp_well in enumerate(strip_wells):
        p20.pick_up_tip()
        p20.aspirate(6, samp_well)  # 2 ul * 3 replicates
        for j in range(3):
            well = dest_wells[i*3 + j]
            p20.dispense(2, well, mix_after=(3, 5))
        p20.drop_tip()

    # deactivate temperature module
    temp_mod.deactivate()
