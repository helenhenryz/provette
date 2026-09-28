from opentrons import protocol_api

metadata = {
    'protocolName': 'BSA Standard Curve',
    'apiLevel': '2.19'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    stock_tube = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 2)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 3)
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 4)
    
    # Define liquids
    water = protocol.define_liquid(
        name='water', description='H2O', display_color='#00FFFF'
    )
    bsa = protocol.define_liquid(
        name='bsa', description='BSA 2 mg/ml', display_color='#000000'
    )
    
    # Load liquids into containers
    stock_tube['A1'].load_liquid(liquid=bsa, volume=1000)  # 1000 µL of BSA
    reservoir['A1'].load_liquid(liquid=water, volume=2000)  # 2000 µL of water
    
    # Load pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tip_rack])
    
    # Pick up tip
    p300.pick_up_tip()
    
    # Well 1: transfer 100 µL from stock to plate A1
    p300.aspirate(100, stock_tube['A1'])
    p300.dispense(100, plate['A1'])
    p300.mix(3, 10, plate['A1'])
    
    # Wells 2-8: serial dilution
    for i in range(2, 9):
        well_name = f'A{i}'
        # Add 50 µL water
        p300.aspirate(50, reservoir['A1'])
        p300.dispense(50, plate[well_name])
        # Transfer 50 µL from previous well
        source_well = f'A{i-1}'
        p300.aspirate(50, plate[source_well])
        p300.dispense(50, plate[well_name])
        # Mix
        p300.mix(3, 10, plate[well_name])
    
    # Remove excess from last well
    p300.aspirate(50, plate['A8'])
    p300.drop_tip()
