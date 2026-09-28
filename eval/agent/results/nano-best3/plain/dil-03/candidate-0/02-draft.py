from opentrons import protocol_api

metadata = {'protocolName': 'BSA Standard Curve', 'apiLevel': '2.19'}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 2)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 1)
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 4)
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips])
    # Define liquids
    bsa = protocol.define_liquid(name='bsa', description='BSA stock', display_color='#FF0000')
    water = protocol.define_liquid(name='water', description='Water', display_color='#0000FF')
    # Load liquids into source wells
    bsa_tube = tuberack['A1']
    bsa_tube.load_liquid(liquid=bsa, volume=200)  # load 200 ul of bsa
    water_well = reservoir['A1']
    water_well.load_liquid(liquid=water, volume=1000)  # load 1000 ul of water
    waste_well = reservoir['A2']  # waste reservoir well
    # Define wells for standards
    wells = ['A1','A2','A3','A4','A5','A6','A7','A8']
    prev_well_name = None
    for i, well_name in enumerate(wells):
        # Pick up a fresh tip for each well
        p300.pick_up_tip()
        well = plate[well_name]
        # Determine diluent volume
        if i == 0:
            diluent_vol = 0
        else:
            diluent_vol = 50
        # Determine transfer volume and source
        if i == 0:
            transfer_vol = 100
            source = tuberack['A1']
        else:
            transfer_vol = 50
            source = plate[prev_well_name]
        # Add diluent (water) if needed
        if diluent_vol > 0:
            p300.aspirate(diluent_vol, water_well)
            p300.dispense(diluent_vol, well)
            # Mix after addition
            p300.mix(5, 40, well)  # 5 cycles of 40 ul mixing
        # Transfer in from source
        p300.aspirate(transfer_vol, source)
        p300.dispense(transfer_vol, well)
        # Update previous well name
        prev_well_name = well_name
        # Drop tip
        p300.drop_tip()
    # Remove 50 ul from the last well to waste
    p300.pick_up_tip()
    p300.aspirate(50, plate['A8'])
    p300.dispense(50, waste_well)
    p300.drop_tip()
    # Add a blank well of water as a negative control
    p300.pick_up_tip()
    p300.aspirate(50, water_well)
    p300.dispense(50, plate['A9'])  # use well A9 as blank
    p300.drop_tip()
