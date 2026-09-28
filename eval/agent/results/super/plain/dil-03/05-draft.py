from opentrons import protocol_api

metadata = {"protocolName": "BSA standard curve for Bradford", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', 2)
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 1)
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 3)
    
    # liquids
    water = protocol.define_liquid(name='water', description='Water diluent', display_color='#FFFFFF')
    bsa = protocol.define_liquid(name='bsa', description='BSA stock 2 mg/ml', display_color='#FF0000')
    
    # load liquids into tubes
    tuberack['A1'].load_liquid(liquid=bsa, volume=500)   # BSA stock
    tuberack['A2'].load_liquid(liquid=water, volume=500) # water
    
    # pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tips])
    
    std_wells = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']
    
    # Serial dilution as per dilution_series guidance: keep tip for whole series
    p20.pick_up_tip()
    for i, well_name in enumerate(std_wells):
        dest = plate[well_name]
        if i == 0:
            # well 1: no diluent, transfer 100 ul from stock
            p20.transfer(100, tuberack['A1'], dest, new_tip='never')
        else:
            # wells 2-8: add 50 ul water, then transfer 50 ul from previous well
            p20.transfer(50, tuberack['A2'], dest, new_tip='never')   # water
            p20.transfer(50, plate[std_wells[i-1]], dest, new_tip='never')  # BSA from previous well
        p20.mix(3, 20, dest)
    p20.drop_tip()
    
    # Blank well: water only (e.g., A9) using fresh tip
    p20.pick_up_tip()
    p20.transfer(50, tuberack['A2'], plate['A9'], new_tip='never')
    p20.drop_tip()
    
    # No waste removal; leaving 100 ul in last well acceptable.
    
