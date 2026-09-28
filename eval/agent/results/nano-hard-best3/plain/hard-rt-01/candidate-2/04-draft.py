from opentrons import protocol_api

metadata = {
    "protocolName": "Reverse Transcription Setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x RT buffer", display_color="#0000FF")
    rt = protocol.define_liquid(name="rt", description="Reverse transcriptase", display_color="#FF0000")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#00FF00")
    primers = protocol.define_liquid(name="primers", description="Random primers", display_color="#FFFF00")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    
    # Define RNA samples
    rna_liquids = {}
    for i in range(1, 13):
        rna_liquids[f"rna {i}"] = protocol.define_liquid(name=f"rna {i}", description=f"RNA sample {i}", display_color="#808080")
    
    # Load labware
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 1)  # PCR plate
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Load temperature module and block
    temp_mod = protocol.load_module("temperature module gen2", 3)
    cold_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    temp_mod.set_temperature(4)  # keep block cold
    
    # Load RNA samples into source plate wells
    source_wells = source_plate.wells()
    for i in range(12):
        source_wells[i].load_liquid(liquid=rna_liquids[f"rna {i+1}"], volume=20)
    
    # Load master liquids into cold block wells
    cold_block["A1"].load_liquid(liquid=buffer, volume=200)  # 5x RT buffer
    cold_block["A2"].load_liquid(liquid=rt, volume=200)      # Reverse transcriptase
    cold_block["A3"].load_liquid(liquid=dntp, volume=200)    # dNTP mix
    cold_block["A4"].load_liquid(liquid=primers, volume=200) # Random primers
    cold_block["A5"].load_liquid(liquid=water, volume=200)   # Water
    
    # Get destination wells
    dest_wells = dest_plate.wells()
    reaction_wells = dest_wells[0:12]   # First 12 wells for RT reactions
    no_rt_wells = dest_wells[12:24]     # Next 12 wells for no-RT controls
    
    # ----- Add shared liquids to reaction wells (buffer, water) -----
    # buffer (4 ul) - shared, dispense into all reaction wells
    p20.pick_up_tip()
    for well in reaction_wells:
        p20.aspirate(4, cold_block["A1"]); p20.dispense(4, well); 
    p20.drop_tip()
    
    # water (5 ul) - shared, dispense into all reaction wells
    p20.pick_up_tip()
    for well in reaction_wells:
        p20.aspirate(5, cold_block["A5"]); p20.dispense(5, well); 
    p20.drop_tip()
    
    # ----- Process each reaction well -----
    for i, well in enumerate(reaction_wells):
        # RNA sample (8 ul)
        p20.pick_up_tip()
        p20.aspirate(8, source_wells[i]); p20.dispense(8, well); 
        p20.drop_tip()
        
        # dNTPs (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A3"]); p20.dispense(1, well); 
        p20.drop_tip()
        
        # primers (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A4"]); p20.dispense(1, well); 
        p20.drop_tip()
        
        # reverse transcriptase (1 ul, last)
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A2"]); p20.dispense(1, well); 
        p20.drop_tip()
    
    # ----- Add shared liquids to no-RT wells (buffer, water) -----
    # buffer (4 ul) - shared, dispense into all no-RT wells
    p20.pick_up_tip()
    for well in no_rt_wells:
        p20.aspirate(4, cold_block["A1"]); p20.dispense(4, well); 
    p20.drop_tip()
    
    # water (6 ul) - shared, dispense into all no-RT wells
    p20.pick_up_tip()
    for well in no_rt_wells:
        p20.aspirate(6, cold_block["A5"]); p20.dispense(6, well); 
    p20.drop_tip()
    
    # ----- Process each no-RT well -----
    for i, well in enumerate(no_rt_wells):
        # RNA sample (8 ul)
        p20.pick_up_tip()
        p20.aspirate(8, source_wells[i]); p20.dispense(8, well); 
        p20.drop_tip()
        
        # dNTPs (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A3"]); p20.dispense(1, well); 
        p20.drop_tip()
        
        # primers (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A4"]); p20.dispense(1, well); 
        p20.drop_tip()
    
    # Deactivate temperature module
    temp_mod.deactivate()
