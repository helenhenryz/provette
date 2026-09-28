from opentrons import protocol_api

metadata = {"protocolName": "Normalization", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    sample_liquids = [protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#FF0000") for i in range(1,25)]
    
    # Hard-coded volumes from normalisation
    sample_volumes = [5.88, 4.17, 11.36, 7.46, 2.38, 5.26, 15.15, 3.33, 6.41, 8.33, 4.95, 9.09, 2.63, 6.94, 10.42, 3.85, 5.68, 20.0, 7.81, 4.55, 12.82, 2.86, 5.43, 8.62]
    diluent_volumes = [44.12, 45.83, 38.64, 42.54, 47.62, 44.74, 34.85, 46.67, 43.59, 41.67, 45.05, 40.91, 47.37, 43.06, 39.58, 46.15, 44.32, 30.0, 42.19, 45.45, 37.18, 47.14, 44.57, 41.38]
    
    # Load liquids into source plate (samples)
    for i in range(24):
        well_name = chr(ord('A') + i // 12) + str(i % 12 + 1)
        source_plate[well_name].load_liquid(liquid=sample_liquids[i], volume=sample_volumes[i])
    
    # Load water into destination plate wells
    for i in range(24):
        well_name = chr(ord('A') + i // 12) + str(i % 12 + 1)
        dest_plate[well_name].load_liquid(liquid=water, volume=diluent_volumes[i])
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])
    p20.pick_up_tip()
    
    # Transfer samples
    for i in range(24):
        well_name = chr(ord('A') + i // 12) + str(i % 12 + 1)
        p20.aspirate(sample_volumes[i], source_plate[well_name])
        p20.dispense(sample_volumes[i], dest_plate[well_name])
    
    p20.drop_tip()
