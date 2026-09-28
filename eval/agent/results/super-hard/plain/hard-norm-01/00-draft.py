import math
from opentrons import protocol_api

metadata = {"protocolName": "Normalize 48 libraries to 4 nM in 20 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips300 = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    source_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 2)
    dest_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 4)
    
    # Pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips300])
    
    # Define liquids
    buffer_liq = protocol.define_liquid(name='buffer', description=' elution buffer', display_color='#00FF00')
    # Assign buffer to reservoir well A1
    reservoir['A1'].load_liquid(liquid=buffer_liq, volume=150000)  # plenty
    
    # Define library liquids
    lib_liquids = {}
    for i in range(1, 49):
        name = f'library {i}'
        liq = protocol.define_liquid(name=name, description=f'Library {i}', display_color='#FFA500')
        lib_liquids[name] = liq
        # Assuming each library in source plate well corresponding to i-1
        well_idx = i-1
        row = well_idx % 8
        col = well_idx // 8 + 1
        well_name = f'{chr(65+row)}{col}'
        source_plate[well_name].load_liquid(liquid=liq, volume=100)  # reasonable starting volume
    
    # Normalization data computed externally (hardcoded from normalise tool)
    norm_data = [
        (6.67, 13.33), (1.78, 18.22), (10.0, 10.0), (1.0, 19.0), (2.42, 17.58), (14.55, 5.45),
        (1.33, 18.67), (3.81, 16.19), (5.71, 14.29), (8.89, 11.11), (1.11, 18.89), (2.96, 17.04),
        (13.33, 6.67), (2.0, 18.0), (4.44, 15.56), (1.45, 18.55), (7.27, 12.73), (2.67, 17.33),
        (10.67, 9.33), (1.23, 18.77), (3.33, 16.67), (5.0, 15.0), (1.67, 18.33), (8.0, 12.0),
        (2.22, 17.78), (6.15, 13.85), (1.14, 18.86), (3.64, 16.36), (9.41, 10.59), (1.6, 18.4),
        (2.76, 17.24), (4.21, 15.79), (1.9, 18.1), (5.33, 14.67), (1.29, 18.71), (3.2, 16.8),
        (12.31, 7.69), (2.11, 17.89), (4.71, 15.29), (1.05, 18.95), (4.0, 16.0), (8.42, 11.58),
        (1.38, 18.62), (2.58, 17.42), (6.4, 13.6), (1.82, 18.18), (3.48, 16.52), (11.43, 8.57)
    ]
    
    # Perform normalization
    for i, (sample_vol, diluent_vol) in enumerate(norm_data, start=1):
        # Map source and destination wells
        src_idx = i-1
        src_row = src_idx % 8
        src_col = src_idx // 8 + 1
        src_well = f'{chr(65+src_row)}{src_col}'
        dst_well = src_well  # same layout in destination plate
        
        # Add diluent first (buffer) using fresh tip
        p300.pick_up_tip()
        p300.aspirate(diluent_vol, reservoir['A1'])
        p300.dispense(diluent_vol, dest_plate[dst_well])
        p300.drop_tip()
        
        # Transfer sample
        p300.pick_up_tip()
        p300.aspirate(sample_vol, source_plate[src_well])
        p300.dispense(sample_vol, dest_plate[dst_well])
        p300.mix(3, 20, dest_plate[dst_well])  # mix in destination
        p300.drop_tip()
    
    protocol.comment('Normalization complete')
