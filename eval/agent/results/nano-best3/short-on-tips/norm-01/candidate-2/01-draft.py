from opentrons import protocol_api

metadata = {
    "protocolName": "Normalization of DNA samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    water_liquid = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    reservoir["A1"].load_liquid(liquid=water_liquid, volume=2000)
    
    for i in range(1, 25):
        sample_liquid = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#FF0000")
        row = (i-1)//12
        col = (i-1)%12
        well_name = f"{chr(65+row)}{col+1}"
        src_well = source_plate.well(well_name)
        src_well.load_liquid(liquid=sample_liquid, volume=100)
    
    # Define volumes from normalisation
    sample_volumes = [5.88, 4.17, 11.36, 7.46, 2.38, 5.26, 15.15, 3.33, 6.41, 8.33, 4.95, 9.09, 2.63, 6.94, 10.42, 3.85, 5.68, 20.0, 7.81, 4.55, 12.82, 2.86, 5.43, 8.62]
    water_volumes = [44.12, 45.83, 38.64, 42.54, 47.62, 44.74, 34.85, 46.67, 43.59, 41.67, 45.05, 40.91, 47.37, 43.06, 39.58, 46.15, 44.32, 30.0, 42.19, 45.45, 37.18, 47.14, 44.57, 41.38]
    
    # Transfer to destination plate
    p300.pick_up_tip()
    for i in range(1, 25):
        row = (i-1)//12
        col = (i-1)%12
        well_name = f"{chr(65+row)}{col+1}"
        dest_well = dest_plate.well(well_name)
        src_well = source_plate.well(well_name)
        
        # Aspirate water and dispense into destination well
        p300.aspirate(water_volumes[i-1], reservoir["A1"])
        p300.dispense(water_volumes[i-1], dest_well)
        
        # Aspirate sample and dispense into destination well
        p300.aspirate(sample_volumes[i-1], src_well)
        p300.dispense(sample_volumes[i-1], dest_well)
    
    # Drop tip
    p300.drop_tip()
