from opentrons import protocol_api

metadata = {'protocolName': 'Pool 5 ul from each of 48 libraries into a tube', 'apiLevel': '2.19'}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', 1)
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 3)
    
    # Load pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tip_rack])
    
    # Define liquids (libraries 1-48)
    for i in range(1, 49):
        protocol.define_liquid(
            name=f'library {i}',
            description=f'Sequencing library {i}',
            display_color='#FF0000'
        )
    
    # Load each library into its source well (A1-D12)
    for i in range(1, 49):
        # Calculate column and row
        col_idx = (i - 1) // 12  # 0-3 for A-D
        row_idx = (i - 1) % 12 + 1  # 1-12
        col_letter = chr(ord('A') + col_idx)
        well_name = f'{col_letter}{row_idx}'
        # Load 100 ul of the library into the well
        plate.well(well_name).load_liquid(
            liquid=f'library {i}',
            volume=100
        )
    
    # Destination tube
    dest_tube = tube_rack.well('A1')
    
    # Pool 5 ul from each library into the destination tube
    for i in range(1, 49):
        # Calculate column and row
        col_idx = (i - 1) // 12
        row_idx = (i - 1) % 12 + 1
        col_letter = chr(ord('A') + col_idx)
        well_name = f'{col_letter}{row_idx}'
        # Pick up tip
        p20.pick_up_tip()
        # Aspirate 5 ul from source well
        p20.aspirate(5, plate.well(well_name))
        # Dispense 5 ul into destination tube
        p20.dispense(5, dest_tube)
        # Drop tip
        p20.drop_tip()
