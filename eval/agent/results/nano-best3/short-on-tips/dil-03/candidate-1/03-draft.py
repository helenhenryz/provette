from opentrons import protocol_api

metadata = {
    'protocolName': 'BSA Standard Curve',
    'apiLevel': '2.19'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tip_rack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 2)
    stock_tube = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 3)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 4)
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 5)
    
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
    
    # Add blank well of water (well H1) as a negative control
    plate['H1'].load_liquid(liquid=water, volume=50)  # 50 µL of water as blank
    
    # Load pipettes
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tip_rack_300])
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tip_rack_20])
    
    # Pick up tip for first well with p300
    p300.pick_up_tip()
    
    # Well 1: transfer 100 µL from stock to plate A1
    p300.aspirate(100, stock_tube['A1'])
    p300.dispense(100, plate['A1'])
    # Mix with 80 µL, 5 strokes
    p300.mix(5, 80, plate['A1'])
    
    # Drop tip to avoid contaminating water
    p300.drop_tip()
    
    # Loop for wells 2-8
    for i in range(2, 9):
        well_name = f'A{i}'
        # Use p20 to add 50 µL water
        p20.pick_up_tip()
        p20.aspirate(50, reservoir['A1'])
        p20.dispense(50, plate[well_name])
        # Transfer 50 µL from previous well
        source_well = f'A{i-1}'
        p20.aspirate(50, plate[source_well])
        # Dispense into well from above to avoid contamination
        p20.dispense(50, plate[well_name].top())
        # Mix with 80 µL, 5 strokes using p300
        p300.pick_up_tip()
        p300.mix(5, 80, plate[well_name])
        p300.drop_tip()
        # Drop p20 tip after mixing
        p20.drop_tip()
    
    # Remove excess from last well using p300
    p300.pick_up_tip()
    p300.aspirate(50, plate['A8'])
    p300.drop_tip()
