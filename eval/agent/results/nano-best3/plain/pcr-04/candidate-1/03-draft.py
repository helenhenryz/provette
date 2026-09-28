from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_setup_6samples_triplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    master_mix_tuberack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    temp_module = protocol.load_module("temperature module gen2", 4)
    cDNA_block = temp_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    
    # Define liquids
    master_mix_liquid = protocol.define_liquid(name="master mix", description="SYBR master mix with primers", display_color="#FF0000")
    sample_1_liquid = protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    sample_2_liquid = protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    sample_3_liquid = protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    sample_4_liquid = protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    sample_5_liquid = protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    sample_6_liquid = protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#800080")
    water_liquid = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#000000")
    
    # Load liquids
    master_mix_tuberack["A1"].load_liquid(liquid=master_mix_liquid, volume=1000)
    cDNA_block["A1"].load_liquid(liquid=sample_1_liquid, volume=200)
    cDNA_block["A2"].load_liquid(liquid=sample_2_liquid, volume=200)
    cDNA_block["A3"].load_liquid(liquid=sample_3_liquid, volume=200)
    cDNA_block["A4"].load_liquid(liquid=sample_4_liquid, volume=200)
    cDNA_block["A5"].load_liquid(liquid=sample_5_liquid, volume=200)
    cDNA_block["A6"].load_liquid(liquid=sample_6_liquid, volume=200)
    water_reservoir["A1"].load_liquid(liquid=water_liquid, volume=1000)
    
    # Set temperature
    temp_module.set_temperature(4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Destination wells: 18 reaction wells (6 samples x 3 replicates)
    dest_wells = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4","B5","B6"]
    
    # Transfer master mix and sample (or water for NTC) to each well
    for i, well in enumerate(dest_wells):
        # Aspirate and dispense 8 ul master mix
        p20.pick_up_tip()
        p20.aspirate(8, master_mix_tuberack["A1"])
        p20.dispense(8, plate[well])
        p20.drop_tip()
        
        if i == 17:  # Last well: no-template control with water
            # Add water (2 ul) for NTC
            p20.pick_up_tip()
            p20.aspirate(2, water_reservoir["A1"])
            p20.dispense(2, plate[well])
            p20.mix(5, 8, plate[well])
            p20.drop_tip()
        else:
            # Normal well: add cDNA sample
            sample_num = (i // 3) + 1
            sample_source = cDNA_block["A"+str(sample_num)]
            # Add sample
            p20.pick_up_tip()
            p20.aspirate(2, sample_source)
            p20.dispense(2, plate[well])
            p20.mix(5, 8, plate[well])
            p20.drop_tip()
    
    # Deactivate temperature module
    temp_module.deactivate()
