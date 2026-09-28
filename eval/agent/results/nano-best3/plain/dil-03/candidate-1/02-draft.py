from opentrons import protocol_api

metadata = {"protocolName": "BSA Standard Curve", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    # Load pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    
    # Define liquids
    bsa = protocol.define_liquid(name="bsa", description="BSA stock", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    
    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=bsa, volume=1000)
    reservoir["A1"].load_liquid(liquid=water, volume=2000)
    
    # Destination wells and volumes
    dest_wells = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]
    bsa_volumes = [50, 25, 12.5, 6.25, 3.12, 1.56, 0.78, 0.39]
    water_volumes = [0, 25, 37.5, 43.75, 46.88, 48.44, 49.22, 49.61]
    
    # Prepare transfers
    for i in range(len(dest_wells)):
        dest = plate[dest_wells[i]]
        bsa_vol = bsa_volumes[i]
        water_vol = water_volumes[i]
        
        # Choose pipette for BSA transfer based on volume
        if bsa_vol > 20:
            aspirator = p300
        else:
            aspirator = p20
        
        # Aspirate and dispense BSA
        aspirator.pick_up_tip()
        aspirator.aspirate(bsa_vol, tubes["A1"])
        aspirator.dispense(bsa_vol, dest)
        aspirator.drop_tip()
        
        # Aspirate and dispense water if needed
        if water_vol > 0:
            p300.pick_up_tip()
            p300.aspirate(water_vol, reservoir["A1"])
            p300.dispense(water_vol, dest)
            p300.drop_tip()
