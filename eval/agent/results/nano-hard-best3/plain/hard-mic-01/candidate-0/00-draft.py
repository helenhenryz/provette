from opentrons import protocol_api

metadata = {
    "protocolName": "MIC plate for 2 antibiotics",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    antibiotic_1 = protocol.define_liquid("antibiotic 1", "Antibiotic 1 stock solution", display_color='#1f77b4')
    antibiotic_2 = protocol.define_liquid("antibiotic 2", "Antibiotic 2 stock solution", display_color='#ff7f0e')
    broth = protocol.define_liquid("broth", "Mueller-Hinton broth", display_color='#2ca02c')
    culture = protocol.define_liquid("culture", "Bacterial culture", display_color='#d62728')
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=antibiotic_1, volume=2000)
    tuberack["A2"].load_liquid(liquid=antibiotic_2, volume=2000)
    reservoir["A1"].load_liquid(liquid=broth, volume=2000)
    tuberack["A3"].load_liquid(liquid=culture, volume=2000)
    
    # Waste well
    waste_well = tuberack["A6"]
    
    # Get dilution series for antibiotic 1
    series_result_1 = protocol.dilution_series(
        stock_concentration=1,
        factor=2,
        points=10,
        final_volume_ul=50,
        first_point_is_stock=False
    )
    series_wells = series_result_1["wells"]
    
    # Process row A with antibiotic 1
    for well_info in series_wells:
        col = well_info["well"]
        target_well = plate["A" + str(col)]
        
        # Add diluent (broth)
        p300.pick_up_tip()
        p300.aspirate(well_info["step_1_add_diluent_ul"], reservoir["A1"])
        p300.dispense(well_info["step_1_add_diluent_ul"], target_well)
        p300.mix(well_info["step_1_add_diluent_ul"], repetitions=1)
        p300.drop_tip()
        
        # Transfer from source
        p300.pick_up_tip()
        if well_info["from"] == "stock":
            source = tuberack["A1"]
        else:
            src_num = int(well_info["from"].split()[-1])
            source = plate["A" + str(src_num)]
        p300.aspirate(well_info["step_2_transfer_in_ul"], source)
        p300.dispense(well_info["step_2_transfer_in_ul"], target_well)
        p300.mix(well_info["step_2_transfer_in_ul"], repetitions=1)
        p300.drop_tip()
    
    # Remove excess from last well (A10) to waste
    p300.pick_up_tip()
    p300.aspirate(50, plate["A10"])
    p300.dispense(50, waste_well)
    p300.drop_tip()
    
    # Growth control (A11): 50 ul broth + 50 ul culture
    p300.pick_up_tip()
    p300.aspirate(50, reservoir["A1"])
    p300.dispense(50, plate["A11"])
    p300.drop_tip()
    p300.pick_up_tip()
    p300.aspirate(50, tuberack["A3"])
    p300.dispense(50, plate["A11"])
    p300.drop_tip()
    
    # Sterility control (A12): 100 ul broth
    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["A12"])
    p300.drop_tip()
    
    # Process row B with antibiotic 2
    for well_info in series_wells:
        col = well_info["well"]
        target_well = plate["B" + str(col)]
        
        # Add diluent (broth)
        p300.pick_up_tip()
        p300.aspirate(well_info["step_1_add_diluent_ul"], reservoir["A1"])
        p300.dispense(well_info["step_1_add_diluent_ul"], target_well)
        p300.mix(well_info["step_1_add_diluent_ul"], repetitions=1)
        p300.drop_tip()
        
        # Transfer from source
        p300.pick_up_tip()
        if well_info["from"] == "stock":
            source = tuberack["A2"]
        else:
            src_num = int(well_info["from"].split()[-1])
            source = plate["B" + str(src_num)]
        p300.aspirate(well_info["step_2_transfer_in_ul"], source)
        p300.dispense(well_info["step_2_transfer_in_ul"], target_well)
        p300.mix(well_info["step_2_transfer_in_ul"], repetitions=1)
        p300.drop_tip()
    
    # Remove excess from last well (B10) to waste
    p300.pick_up_tip()
    p300.aspirate(50, plate["B10"])
    p300.dispense(50, waste_well)
    p300.drop_tip()
    
    # Growth control (B11): 50 ul broth + 50 ul culture
    p300.pick_up_tip()
    p300.aspirate(50, reservoir["A1"])
    p300.dispense(50, plate["B11"])
    p300.drop_tip()
    p300.pick_up_tip()
    p300.aspirate(50, tuberack["A3"])
    p300.dispense(50, plate["B11"])
    p300.drop_tip()
    
    # Sterility control (B12): 100 ul broth
    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["B12"])
    p300.drop_tip()
