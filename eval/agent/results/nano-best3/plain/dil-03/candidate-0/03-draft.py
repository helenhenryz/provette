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
    # Load liquids
    bsa_tube = tuberack['A1']
    bsa_tube.load_liquid(liquid=bsa, volume=100)  # 100 ul of stock BSA
    water_reservoir = reservoir['A1']
    water_reservoir.load_liquid(liquid=water, volume=400)  # enough water for diluent additions
    waste_well = reservoir['A2']  # waste destination
    # Define the 8 wells for the standards
    wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']
    prev_source = None
    for i, well_name in enumerate(wells):
        p300.pick_up_tip()
        well = plate[well_name]
        # Determine diluent and transfer volumes
        if i == 0:
            diluent_vol = 0
            transfer_vol = 100
            source = bsa_tube
        else:
            diluent_vol = 50
            transfer_vol = 50
            source = plate[prev_source]
        # Add diluent (water) if required
        if diluent_vol > 0:
            p300.aspirate(diluent_vol, water_reservoir)
            p300.dispense(diluent_vol, well)
            p300.mix(5, 40, well)  # mix the added water
        # Transfer the sample
        p300.aspirate(transfer_vol, source)
        p300.dispense(transfer_vol, well)
        # Mix the combined volume
        total_vol = diluent_vol + transfer_vol
        p300.mix(5, 40, well)
        # Drop tip and move to next well
        p300.drop_tip()
        prev_source = well_name
    # Remove 50 ul from the last well to waste
    p300.pick_up_tip()
    p300.aspirate(50, plate['A8'])
    p300.dispense(50, waste_well)
    p300.drop_tip()
