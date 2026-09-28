from opentrons import protocol_api

metadata = {
    "protocolName": "PCR plate prep: 18ul master mix + 2ul template",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "2")
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "3")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "4")
    
    # Define master mix
    master_mix = protocol.define_liquid(
        name="master mix",
        description="Master mix for PCR",
        display_color="#FF0000"
    )
    # Load master mix into reservoir well A1
    reservoir_well = reservoir["A1"]
    reservoir_well.load_liquid(liquid=master_mix, volume=2000)
    
    # Define each sample as its own liquid and load into its well
    for i, well in enumerate(source_plate.wells()):
        liquid_name = f"sample_{i+1}"
        sample_liquid = protocol.define_liquid(
            name=liquid_name,
            description=f"Sample {i+1}",
            display_color=f"#{i:06X}"
        )
        # Load 10 ul of each sample into its well
        well.load_liquid(liquid=sample_liquid, volume=10)
    
    # Load the p20 multi-channel pipette
    p20_multi = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tip_rack])
    
    # Get all destination and source wells in order
    dest_wells = list(pcr_plate.wells())
    src_wells = list(source_plate.wells())
    
    # Process in batches of 8
    p20_multi.pick_up_tip()
    for i in range(0, 96, 8):
        dest_group = dest_wells[i:i+8]
        src_group = src_wells[i:i+8]
        
        # Aspirate 18 ul of master mix from reservoir into all 8 channels
        p20_multi.aspirate(18, reservoir["A1"])
        # Dispense 18 ul into each destination well
        p20_multi.dispense(18, dest_group)
        # Aspirate 2 ul from each source well (template)
        p20_multi.aspirate(2, src_group)
        # Dispense 2 ul into each destination well
        p20_multi.dispense(2, dest_group)
    
    # Drop tip
    p20_multi.drop_tip()
