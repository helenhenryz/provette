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
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)
    
    # Define each sample and load 10 ul into its well
    for i, well in enumerate(source_plate.wells()):
        sample_liquid = protocol.define_liquid(
            name=f"sample_{i+1}",
            description=f"Sample {i+1}",
            display_color=f"#{i:06X}"
        )
        well.load_liquid(liquid=sample_liquid, volume=10)
    
    # Load the p20 multi-channel pipette
    p20_multi = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tip_rack])
    
    # Process each well individually
    p20_multi.pick_up_tip()
    for i, dest_well in enumerate(pcr_plate.wells()):
        src_well = source_plate.wells()[i]
        # Add 18 ul master mix
        p20_multi.aspirate(18, reservoir["A1"])
        p20_multi.dispense(18, dest_well)
        # Add 2 ul template
        p20_multi.aspirate(2, src_well)
        p20_multi.dispense(2, dest_well)
    # Drop tip
    p20_multi.drop_tip()
