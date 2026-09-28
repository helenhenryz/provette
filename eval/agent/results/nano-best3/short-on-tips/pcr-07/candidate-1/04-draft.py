from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_12_samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    temp_mod = protocol.load_module("temperature module gen2", 1)
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    
    # Define liquids
    # Sample liquids
    for i in range(1, 13):
        sample_liquid = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i} DNA template",
            display_color="#FF0000"
        )
        if i <= 6:
            well_name = f"A{i}"
        else:
            well_name = f"B{i-6}"
        well = block[well_name]
        well.load_liquid(liquid=sample_liquid, volume=100)
    
    # Buffer
    buffer_liquid = protocol.define_liquid(
        name="buffer",
        description="PCR buffer",
        display_color="#0000FF"
    )
    buffer_well = block["C1"]
    buffer_well.load_liquid(liquid=buffer_liquid, volume=500)
    
    # Polymerase
    polymerase_liquid = protocol.define_liquid(
        name="polymerase",
        description="DNA polymerase",
        display_color="#00FF00"
    )
    polymerase_well = block["C2"]
    polymerase_well.load_liquid(liquid=polymerase_liquid, volume=10)
    
    # Fwd primer
    fwd_primer_liquid = protocol.define_liquid(
        name="fwd primer",
        description="Forward primer",
        display_color="#FFAA00"
    )
    fwd_primer_well = block["C3"]
    fwd_primer_well.load_liquid(liquid=fwd_primer_liquid, volume=50)
    
    # Rev primer
    rev_primer_liquid = protocol.define_liquid(
        name="rev primer",
        description="Reverse primer",
        display_color="#AA00FF"
    )
    rev_primer_well = block["C4"]
    rev_primer_well.load_liquid(liquid=rev_primer_liquid, volume=50)
    
    # Water
    water_liquid = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#00FFFF"
    )
    water_well = block["C5"]
    water_well.load_liquid(liquid=water_liquid, volume=500)
    
    # Load pipette and pick up tip
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    p20.pick_up_tip()
    
    # Create master mix in well D1
    master_mix_well = block["D1"]
    
    # Add water (126 ul) first
    for vol in [20, 20, 20, 20, 20, 20, 6]:
        p20.aspirate(vol, water_well)
        p20.dispense(vol, master_mix_well)
    
    # Add fwd primer (12 ul)
    p20.aspirate(12, fwd_primer_well)
    p20.dispense(12, master_mix_well)
    
    # Add rev primer (12 ul)
    p20.aspirate(12, rev_primer_well)
    p20.dispense(12, master_mix_well)
    
    # Add polymerase (6 ul) last
    p20.aspirate(6, polymerase_well)
    p20.dispense(6, master_mix_well)
    
    # Mix master mix (5 cycles of 13 ul)
    protocol.mix(5, master_mix_well)
    
    # Transfer to each of the 12 destination wells
    for i in range(1, 13):
        # Destination well
        dest_well = plate[f"A{i}"]
        
        # Add buffer (10 ul)
        p20.aspirate(10, buffer_well)
        p20.dispense(10, dest_well)
        
        # Add sample (2 ul)
        if i <= 6:
            sample_source_well = block[f"A{i}"]
        else:
            sample_source_well = block[f"B{i-6}"]
        p20.aspirate(2, sample_source_well)
        p20.dispense(2, dest_well)
        
        # Add master mix (13 ul)
        p20.aspirate(13, master_mix_well)
        p20.dispense(13, dest_well)
    
    # Drop tip
    p20.drop_tip()
