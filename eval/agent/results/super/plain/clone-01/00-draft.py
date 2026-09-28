import json
from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digests Setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 1)
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 2)
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', 3)
    
    # Pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])
    
    # Define liquids
    plasmids = [f'plasmid {i}' for i in range(1, 13)]
    liquid_names = plasmids + ['water', 'buffer', 'enzyme']
    liquids = {}
    for name in liquid_names:
        liquids[name] = protocol.define_liquid(
            name=name,
            description=f'{name} stock',
            display_color='#FFFFFF' if name.startswith('plasmid') else ('#0000FF' if name=='water' else '#FF0000' if name=='buffer' else '#00FF00')
        )
    
    # Load liquids into tubes (assign positions)
    # Map plasmid 1-12 to A1-A12 (column-wise)
    positions = [
        'A1','A2','A3','A4','A5','A6','B1','B2','B3','B4','B5','B6',
        'C1','C2','C3','C4','C5','C6','D1','D2','D3','D4','D5','D6'
    ]
    # Assign first 12 to plasmids
    for i, name in enumerate(plasmids):
        tube_rack[positions[i]].load_liquid(liquids[name], volume=100)  # ul
    # Water, buffer, enzyme
    tube_rack[positions[12]].load_liquid(liquids['water'], volume=500)
    tube_rack[positions[13]].load_liquid(liquids['buffer'], volume=500)
    tube_rack[positions[14]].load_liquid(liquids['enzyme'], volume=200)
    
    # Master mix pooling (buffer 2ul, enzyme 1ul, water 12ul per reaction, 12 reactions +10%)
    # Calculate volumes to pool
    vol_buffer = 2.0 * 12 * 1.1   # 26.4 ul
    vol_enzyme = 1.0 * 12 * 1.1   # 13.2 ul
    vol_water  = 12.0 * 12 * 1.1  # 158.4 ul
    
    # Use a tube for mixing master mix (e.g., position D6)
    mix_tube = tube_rack['D6']
    
    # Pool components
    p20.pick_up_tip()
    # Buffer
    p20.aspirate(vol_buffer, tube_rack[positions[13]])  # buffer tube
    p20.dispense(vol_buffer, mix_tube)
    # Enzyme
    p20.aspirate(vol_enzyme, tube_rack[positions[14]])  # enzyme tube
    p20.dispense(vol_enzyme, mix_tube)
    # Water
    p20.aspirate(vol_water, tube_rack[positions[12]])   # water tube
    p20.dispense(vol_water, mix_tube)
    p20.mix(3, 20, mix_tube)  # mix in tube
    p20.drop_tip()
    
    # Distribute master mix to each well (15 ul per well)
    # Wells in order A1..A12 (down columns)
    well_order = [f'{row}{col}' for col in range(1,13) for row in ['A','B','C','D','E','F','G','H']][:12]
    p20.pick_up_tip()
    for well in well_order:
        p20.aspirate(15.0, mix_tube)
        p20.dispense(15.0, plate[well])
        p20.mix(2, 10, plate[well])
    p20.drop_tip()
    
    # Add plasmids (5 ul each) to corresponding wells
    for i, (name, well) in enumerate(zip(plasmids, well_order)):
        p20.pick_up_tip()
        p20.aspirate(5.0, tube_rack[positions[i]])  # plasmid tube
        p20.dispense(5.0, plate[well])
        p20.mix(2, 10, plate[well])
        p20.drop_tip()
