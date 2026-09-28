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
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Load temperature module and block
    temp_mod = protocol.load_module("temperature module gen2", 3)
    cold_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    
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
    
    # Process each sample
    for i in range(12):
        rxn_well = reaction_wells[i]
        no_rt_well = no_rt_wells[i]
        rna_source_well = source_wells[i]
        
        # Pick up a fresh tip
        p20.pick_up_tip()
        
        # Add components to RT reaction well
        p20.aspirate(4, cold_block["A1"]); p20.dispense(4, rxn_well)   # buffer
        p20.aspirate(1, cold_block["A2"]); p20.dispense(1, rxn_well)   # rt
        p20.aspirate(1, cold_block["A3"]); p20.dispense(1, rxn_well)   # dntp
        p20.aspirate(1, cold_block["A4"]); p20.dispense(1, rxn_well)   # primers
        p20.aspirate(5, cold_block["A5"]); p20.dispense(5, rxn_well)   # water
        p20.aspirate(8, rna_source_well); p20.dispense(8, rxn_well)   # RNA sample
        
        # Add components to no-RT control well
        p20.aspirate(4, cold_block["A1"]); p20.dispense(4, no_rt_well)   # buffer
        p20.aspirate(1, cold_block["A3"]); p20.dispense(1, no_rt_well)   # dntp
        p20.aspirate(1, cold_block["A4"]); p20.dispense(1, no_rt_well)   # primers
        p20.aspirate(8, rna_source_well); p20.dispense(8, no_rt_well)   # RNA sample
        p20.aspirate(6, cold_block["A5"]); p20.dispense(6, no_rt_well)   # water
        
        # Drop tip after finishing this sample
        p20.drop_tip()
