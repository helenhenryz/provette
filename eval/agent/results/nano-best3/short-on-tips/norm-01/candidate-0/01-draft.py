from opentrons import protocol_api

metadata = {"protocolName": "Normalization_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
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
    for i in range(24):
        p300.pick_up_tip()
        # Aspirate sample
        p300.aspirate(sample_volumes[i], source_plate[well_names[i]])
        # Dispense sample into destination well
        p300.dispense(sample_volumes[i], dest_plate[well_names[i]])
        # Aspirate water
        p300.aspirate(diluent_volumes[i], reservoir["A1"])
        # Dispense water into same destination well
        p300.dispense(diluent_volumes[i], dest_plate[well_names[i]])
        p300.drop_tip()
