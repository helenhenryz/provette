from opentrons import protocol_api

metadata = {
    "protocolName": "BSA Standard Curve",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    waste_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    bsa = protocol.define_liquid(name="bsa", description="BSA stock", display_color="#FF0000")
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=bsa, volume=1000)
    water_reservoir["A1"].load_liquid(liquid=water, volume=1000)
    waste_reservoir["A1"].load_liquid(liquid="waste")
    
    # Define wells for the standard curve
    wells = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]
    
    # Loop over wells to perform serial dilution
    for i, well in enumerate(wells, start=1):
        p300.pick_up_tip()
        
        # Add diluent (water) if needed
        if i > 1:
            diluent_vol = 50
            p300.aspirate(diluent_vol, water_reservoir["A1"])
            p300.dispense(diluent_vol, plate[well])
        
        # Determine transfer volume and source
        if i == 1:
            transfer_vol = 100
            source = tuberack["A1"]
        else:
            transfer_vol = 50
            source = plate[wells[i-2]]
        
        # Transfer from source to well
        p300.aspirate(transfer_vol, source)
        p300.dispense(transfer_vol, plate[well])
        
        # Mix: 5 cycles of aspirate 80 ul and dispense 80 ul
        for _ in range(5):
            p300.aspirate(80, plate[well])
            p300.dispense(80, plate[well])
        
        # If this is the last well, remove 50 ul to waste
        if i == len(wells):
            p300.aspirate(50, plate[well])
            p300.dispense(50, waste_reservoir["A1"])
        
        # Drop tip
        p300.drop_tip()
