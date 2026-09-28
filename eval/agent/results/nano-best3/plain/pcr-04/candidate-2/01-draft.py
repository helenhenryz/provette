from opentrons import protocol_api

metadata = {"protocolName": "qPCR_6samples_triplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 3)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    cDNA_block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="SYBR master mix with primers", display_color="#FF0000")
    sample_1 = protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    sample_2 = protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    sample_3 = protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    sample_4 = protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    sample_5 = protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    sample_6 = protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#FFFFFF")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#000000")

    # Load liquids into source wells
    tube_rack["A1"].load_liquid(liquid=master_mix, volume=200)
    tube_rack["A2"].load_liquid(liquid=water, volume=200)
    cDNA_block["A1"].load_liquid(liquid=sample_1, volume=30)
    cDNA_block["A2"].load_liquid(liquid=sample_2, volume=30)
    cDNA_block["A3"].load_liquid(liquid=sample_3, volume=30)
    cDNA_block["A4"].load_liquid(liquid=sample_4, volume=30)
    cDNA_block["A5"].load_liquid(liquid=sample_5, volume=30)
    cDNA_block["A6"].load_liquid(liquid=sample_6, volume=30)

    # Set temperature for the aluminium block
    temp_mod.set_temperature(4)

    # Transfer master mix and samples to plate
    target_wells = plate.wells()[:18]  # first 18 wells for reactions
    for i, target_well in enumerate(target_wells):
        # aspirate and dispense master mix (8 ul)
        p20.pick_up_tip()
        p20.aspirate(8, tube_rack["A1"])
        p20.dispense(8, target_well)
        # determine sample number (1-indexed)
        sample_number = i // 3 + 1
        # aspirate sample (2 ul) or water for NTC
        if i < 18:  # regular reaction wells
            sample_source = cDNA_block[f"A{sample_number}"]
            p20.aspirate(2, sample_source)
        else:  # NTC well (should not reach here with current loop)
            p20.aspirate(2, tube_rack["A2"])
        p20.dispense(2, target_well)
        # mix the well after adding sample
        p20.mix(5, 8, target_well)
        p20.drop_tip()

    # Add no‑template control (8 ul master mix + 2 ul water) in an extra well
    # Get the 19th well (index 18) – any empty well works
    NTC_well = plate.wells()[18]
    p20.pick_up_tip()
    p20.aspirate(8, tube_rack["A1"])
    p20.dispense(8, NTC_well)
    p20.aspirate(2, tube_rack["A2"])
    p20.dispense(2, NTC_well)
    p20.mix(5, 10, NTC_well)  # mix the NTC well as well
    p20.drop_tip()

    # Deactivate temperature module after protocol ends
    temp_mod.deactivate()
