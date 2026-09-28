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
    
    # Define liquids and capture the returned objects
    master_mix_liquid = protocol.define_liquid(name="master mix", description="SYBR master mix with primers", display_color="#FF0000")
    sample_1_liquid = protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    sample_2_liquid = protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    sample_3_liquid = protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    sample_4_liquid = protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    sample_5_liquid = protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    sample_6_liquid = protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#800080")
    
    # Load liquids into source wells
    master_mix_tuberack["A1"].load_liquid(liquid=master_mix_liquid, volume=1000)
    cDNA_block["A1"].load_liquid(liquid=sample_1_liquid, volume=1000)
    cDNA_block["A2"].load_liquid(liquid=sample_2_liquid, volume=1000)
    cDNA_block["A3"].load_liquid(liquid=sample_3_liquid, volume=1000)
    cDNA_block["A4"].load_liquid(liquid=sample_4_liquid, volume=1000)
    cDNA_block["A5"].load_liquid(liquid=sample_5_liquid, volume=1000)
    cDNA_block["A6"].load_liquid(liquid=sample_6_liquid, volume=1000)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Destination wells (18 wells) in order
    dest_wells = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4","B5","B6"]
    
    # Transfer master mix and sample to each well
    for i, well in enumerate(dest_wells):
        # Determine which sample this well belongs to (1-6)
        sample_num = (i // 3) + 1  # integer division, groups of 3
        
        # Pick up tip
        p20.pick_up_tip()
        
        # Aspirate 8 ul master mix
        p20.aspirate(8, master_mix_tuberack["A1"])
        
        # Dispense 8 ul master mix into destination well
        p20.dispense(8, plate[well])
        
        # Aspirate 2 ul sample
        sample_source = cDNA_block["A"+str(sample_num)]
        p20.aspirate(2, sample_source)
        
        # Dispense 2 ul sample into same destination well (adding to master mix)
        p20.dispense(2, plate[well])
        
        # Drop tip
        p20.drop_tip()
