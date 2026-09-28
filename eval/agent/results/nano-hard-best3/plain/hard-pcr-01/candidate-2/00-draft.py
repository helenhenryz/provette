from opentrons import protocol_api

metadata = {"protocolName": "qPCR_setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define the master mix liquid
    protocol.define_liquid("mix", "Master mix for qPCR", "#FF0000")
    
    # Load the source plate (samples)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    
    # Define and load each sample as its own liquid
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well_name = row + str(col)
            source_liquid_name = f"source_{well_name}"
            protocol.define_liquid(source_liquid_name, f"Sample from {well_name}", "#00FF00")
            # Load 100 ul of each sample into its well
            source_plate[well_name].load_liquid(liquid=source_liquid_name, volume=100)
    
    # Load reservoir for master mix
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    reservoir["A1"].load_liquid(liquid="mix", volume=1600)
    
    # Load tip rack and p20 pipette
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    
    # Load the qPCR plate (destination)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    
    # Transfer 15 ul mix + 5 ul template to each well
    for row in "ABCDEFGH":
        for col in range(1, 13):
            dest_well = row + str(col)
            p20.pick_up_tip()
            # Aspirate 15 ul of master mix
            p20.aspirate(15, reservoir["A1"])
            # Dispense 15 ul mix into destination well
            p20.dispense(15, pcr_plate[dest_well])
            # Aspirate 5 ul from the matching source well
            p20.aspirate(5, source_plate[dest_well])
            # Dispense 5 ul template into the same well
            p20.dispense(5, pcr_plate[dest_well])
            p20.drop_tip()
