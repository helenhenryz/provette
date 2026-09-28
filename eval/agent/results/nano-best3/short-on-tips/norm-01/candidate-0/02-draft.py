from opentrons import protocol_api

metadata = {"protocolName": "Normalization_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip_rack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack_300])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="water", display_color="#0000FF")
    sample_liquids = {}
    for i in range(1, 25):
        sample_liquids[i] = protocol.define_liquid(name=f"sample {i}", description=f"sample {i}", display_color="#000000")
    
    # Define volumes
    sample_volumes = [5.88, 4.17, 11.36, 7.46, 2.38, 5.26, 15.15, 3.33, 6.41, 8.33, 4.95, 9.09, 2.63, 6.94, 10.42, 3.85, 5.68, 20.0, 7.81, 4.55, 12.82, 2.86, 5.43, 8.62]
    diluent_volumes = [44.12, 45.83, 38.64, 42.54, 47.62, 44.74, 34.85, 46.67, 43.59, 41.67, 45.05, 40.91, 47.37, 43.06, 39.58, 46.15, 44.32, 30.0, 42.19, 45.45, 37.18, 47.14, 44.57, 41.38]
    
    # Well names for the 24 samples (row-major order)
    well_names = [f"{chr(65 + i // 12)}{(i % 12) + 1}" for i in range(24)]
    
    # Load sample liquids into source plate wells
    for i in range(24):
        well = source_plate[well_names[i]]
        well.load_liquid(liquid=sample_liquids[i+1], volume=sample_volumes[i])
    
    # Load water into reservoir well A1
    reservoir_well = reservoir["A1"]
    reservoir_well.load_liquid(liquid=water, volume=sum(diluent_volumes))
    
    # Perform transfers
    # Pick up p300 tip once (will be reused for all water transfers)
    p300.pick_up_tip()
    for i in range(24):
        # Use p20 for sample transfer
        p20.pick_up_tip()
        # Aspirate sample
        p20.aspirate(sample_volumes[i], source_plate[well_names[i]])
        # Dispense sample into destination well
        p20.dispense(sample_volumes[i], dest_plate[well_names[i]])
        p20.drop_tip()
        
        # Use p300 for water transfer (same tip reused)
        p300.aspirate(diluent_volumes[i], reservoir["A1"])
        p300.dispense(diluent_volumes[i], dest_plate[well_names[i]])
    p300.drop_tip()
