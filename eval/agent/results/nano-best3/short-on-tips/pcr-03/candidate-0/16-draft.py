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
    
    # Define water for no-template control
    water = protocol.define_liquid(
        name="water",
        description="Water",
        display_color="#0000FF"
    )
    # Load water into reservoir well A2 (sufficient volume)
    reservoir["A2"].load_liquid(liquid=water, volume=30)
    
    # Define each sample and load 30 ul into its well (to ensure enough depth)
    for i, well in enumerate(source_plate.wells()):
        sample_liquid = protocol.define_liquid(
            name=f"sample_{i+1}",
            description=f"Sample {i+1}",
            display_color=f"#{i:06X}"
        )
        well.load_liquid(liquid=sample_liquid, volume=30)  # increased volume
    
    # Load the p20 single-channel pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])
    
    # Process each well individually
    for i, dest_well in enumerate(pcr_plate.wells()):
        src_well = source_plate.wells()[i]
        
        # Add 18 ul master mix (fresh tip)
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"])
        p20.dispense(18, dest_well)
        p20.drop_tip()
        
        # Add 2 ul template or water (fresh tip)
        p20.pick_up_tip()
        if i == 95:  # no-template control well (last well)
            # aspirate 2 ul water for no-template control
            p20.aspirate(2, reservoir["A2"].bottom(0.5))
        else:
            # aspirate 2 ul from source well (aspirate from bottom to stay in liquid)
            p20.aspirate(2, src_well.bottom(0.5))
        p20.dispense(2, dest_well)
        # Mix the well to ensure proper blending
        p20.mix(5, 16, dest_well)
        # Drop tip
        p20.drop_tip()
