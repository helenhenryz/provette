from opentrons import protocol_api

metadata = {"protocolName": "qPCR_setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define the master mix liquid
    master_mix = protocol.define_liquid("mix", "Master mix for qPCR", "#FF0000")
    
    # Define water for no-template control
    water = protocol.define_liquid("water", "Water for no-template control", "#00FFFF")
    
    # Load the source plate (samples)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    
    # Define and load each sample as its own liquid
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well_name = row + str(col)
            source_liquid_name = f"source_{well_name}"
            # Define the liquid and keep the object
            src_liquid_obj = protocol.define_liquid(source_liquid_name, f"Sample from {well_name}", "#00FF00")
            # Load 100 ul of each sample into its well
            source_plate[well_name].load_liquid(liquid=src_liquid_obj, volume=100)
    
    # Load water into a dedicated well for the no-template control
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    water_reservoir["A2"].load_liquid(liquid=water, volume=100)
    
    # Load reservoir for master mix (enough volume to stay above tip)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    reservoir["A1"].load_liquid(liquid=master_mix, volume=1700)  # ~1700 ul keeps tip submerged
    
    # Load tip rack and p20 pipette
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])
    
    # Load the qPCR plate (destination)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    
    # Designate a no-template control well (e.g., A12)
    no_template_well = "A12"
    
    # Transfer 15 ul mix + 5 ul template (or water) to each well
    for row in "ABCDEFGH":
        for col in range(1, 13):
            dest_well = row + str(col)
            p20.pick_up_tip()
            if dest_well == no_template_well:
                # No-template control: aspirate 5 ul water, dispense into well
                p20.aspirate(5, water_reservoir["A2"])
                p20.dispense(5, pcr_plate[dest_well])
                # Aspirate 15 ul master mix
                p20.aspirate(15, reservoir["A1"])
                # Dispense 15 ul mix into well
                p20.dispense(15, pcr_plate[dest_well])
                # Mix the well (≈80% of well volume)
                p20.mix(5, 16, pcr_plate[dest_well])
            else:
                # Regular well: aspirate 5 ul template, dispense into well
                p20.aspirate(5, source_plate[dest_well])
                p20.dispense(5, pcr_plate[dest_well])
                # Aspirate 15 ul master mix
                p20.aspirate(15, reservoir["A1"])
                # Dispense 15 ul mix into well
                p20.dispense(15, pcr_plate[dest_well])
                # Mix the well (≈80% of well volume)
                p20.mix(5, 16, pcr_plate[dest_well])
            p20.drop_tip()
