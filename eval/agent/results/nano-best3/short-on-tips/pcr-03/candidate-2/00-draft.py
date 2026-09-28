from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_96", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Define master mix
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)
    
    # Define sample liquids (one per well) and load them
    for well in source_plate.wells():
        sample_liquid = protocol.define_liquid(
            name=f"sample_{well.name}", description=f"Sample from {well.name}", display_color="#000000"
        )
        well.load_liquid(liquid=sample_liquid, volume=100)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300.pick_up_tip()
    
    # Transfer 18 ul master mix + 2 ul template to each well
    for well in pcr_plate.wells():
        # Add 18 ul master mix
        p300.aspirate(18, reservoir["A1"])
        p300.dispense(18, well)
        # Add 2 ul template from matching source well
        p300.aspirate(2, source_plate[well.name])
        p300.dispense(2, well)
    
    p300.drop_tip()
