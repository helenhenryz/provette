from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_96", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Define master mix
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)
    
    # Define sample liquids (one per well) and load them
    well_names = [row + str(col) for row in "ABCDEFGH" for col in range(1,13)]
    for well_name in well_names:
        sample_liquid = protocol.define_liquid(
            name=f"sample_{well_name}", description=f"Sample from {well_name}", display_color="#000000"
        )
        source_plate[well_name].load_liquid(liquid=sample_liquid, volume=100)
    
    # Load p20 pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Transfer master mix + template to each PCR well
    for well_name in well_names:
        # Add 18 ul master mix
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"])
        p20.dispense(18, pcr_plate[well_name])
        # Add 2 ul template
        p20.aspirate(2, source_plate[well_name])
        p20.dispense(2, pcr_plate[well_name])
        p20.drop_tip()
