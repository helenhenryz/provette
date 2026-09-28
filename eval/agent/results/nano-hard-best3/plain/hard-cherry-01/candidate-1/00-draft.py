from opentrons import protocol_api

metadata = {
    'protocolName': 'Cherrypick 2 ul from 384-well source plate to 96-well PCR plate with master mix',
    'apiLevel': '2.19'
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    mix = protocol.define_liquid(
        name='mix',
        description='PCR master mix',
        display_color='#FF0000'
    )
    
    # Define source liquids (one per source well)
    source_names = ['A1','B2','C3','D4','E5','F6','G7','H8','I9','J10','K11','L12','M13','N14','O15','P16','A17','B18','C19','D20','E21','F22','G23','H24']
    source_liquids = {}
    for name in source_names:
        liquid_name = f'src_{name}'
        source_liquids[name] = protocol.define_liquid(
            name=liquid_name,
            description=f'Sample from {name}',
            display_color='#000000'
        )
    
    # Load labware
    source_plate = protocol.load_labware('corning_384_wellplate_112ul_flat', 2)
    dest_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 3)
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', 1)
    mix_tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 4)
    
    # Load the mix liquid into a tube (A1 of the tube rack)
    mix_tube = mix_tube_rack['A1']
    mix_tube.load_liquid(liquid=mix, volume=500)  # 500 ul is enough for 24 * 18 ul = 432 ul
    
    # Load source liquids into the source plate wells
    for name in source_names:
        src_well = source_plate[name]
        liquid = source_liquids[name]
        src_well.load_liquid(liquid=liquid, volume=100)  # 100 ul starting volume
    
    # Load the pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tip_rack])
    
    # Define the mapping of source and destination wells
    source_coords = ['A1','B2','C3','D4','E5','F6','G7','H8','I9','J10','K11','L12','M13','N14','O15','P16','A17','B18','C19','D20','E21','F22','G23','H24']
    dest_coords = ['A1','B1','C1','D1','E1','F1','G1','H1','A2','B2','C2','D2','E2','F2','G2','H2','A3','B3','C3','D3','E3','F3','G3','H3']
    
    # Perform the transfers
    for i in range(len(source_coords)):
        src_coord = source_coords[i]
        dest_coord = dest_coords[i]
        
        # Pick up tip
        p20.pick_up_tip()
        
        # Aspirate 2 ul from source well
        src_well = source_plate[src_coord]
        p20.aspirate(2, src_well)
        
        # Dispense 2 ul into destination well
        dest_well = dest_plate[dest_coord]
        p20.dispense(2, dest_well)
        
        # Aspirate 18 ul of mix from the tube
        p20.aspirate(18, mix_tube)
        
        # Dispense 18 ul into the same destination well
        p20.dispense(18, dest_well)
        
        # Drop tip
        p20.drop_tip()
