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
    # Load master mix into reservoir well A1 (sufficient volume)
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)
    
    # Define each sample and load 30 ul into its well (to ensure enough depth)
    for i, well in enumerate(source_plate.wells()):
        sample_liquid = protocol.define_liquid(
            name=f"sample_{i+1}",
            description=f"Sample {i+1}",
            display_color=f"#{i:06X}"
        )
        well.load_liquid(liquid=sample_liquid, volume=30)  # increased volume
    
    # Load the p20 multi-channel pipette
    p20_multi = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tip_rack])
    
    # Process in batches of 8
    dest_wells = list(pcr_plate.wells())
    src_wells = list(source_plate.wells())
    
    for i in range(0, 96, 8):
        dest_group = dest_wells[i:i+8]
        src_group = src_wells[i:i+8]
        
        # Fresh tip for each batch
        p20_multi.pick_up_tip()
        
        # Add 18 ul master mix to all 8 destination wells
        p20_multi.aspirate(18, reservoir["A1"])
        for well in dest_group:
            p20_multi.dispense(18, well)
        
        # Add 2 ul template from each source well
        p20_multi.aspirate(2, src_group)
        for well in dest_group:
            p20_multi.dispense(2, well)
        
        # Drop tip after batch
        p20_multi.drop_tip()
