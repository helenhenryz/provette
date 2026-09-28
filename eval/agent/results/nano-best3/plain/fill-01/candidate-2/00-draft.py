from opentrons import protocol_api

metadata = {
    "protocolName": "Fill 96-well deep well plate with LB and inoculate with glycerol stock",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    lb = protocol.define_liquid(
        name="lb",
        description='LB medium (Luria-Bertani)',
        display_color='#0000FF'
    )
    glycerol = protocol.define_liquid(
        name="glycerol_stock",
        description='Glycerol stock cultures',
        display_color='#800080'
    )
    
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    deep_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 3)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tip_racks])
    
    # Load liquids into source wells
    # Load LB into reservoir wells A1-A4 with 15000 µL each
    for i in range(1, 5):
        reservoir_well = reservoir[f"A{i}"]
        reservoir_well.load_liquid(liquid=lb, volume=15000)
    
    # Load glycerol stock into each well of glycerol plate with 1000 µL each
    for well_name in glycerol_plate.well_names():
        well = glycerol_plate[well_name]
        well.load_liquid(liquid=glycerol, volume=1000)
    
    # Prepare list of reservoir wells to use
    reservoir_wells = [reservoir["A1"], reservoir["A2"], reservoir["A3"], reservoir["A4"]]
    current_reservoir_index = 0
    current_reservoir_volume = 15000
    
    # Process each well in the deep plate
    for well_name in deep_plate.well_names():
        # Get the current reservoir well
        source_reservoir_well = reservoir_wells[current_reservoir_index]
        
        # Fill well with 500 µL of LB and inoculate with 5 µL glycerol stock
        p1000.pick_up_tip()
        p1000.aspirate(500, source_reservoir_well)
        p1000.dispense(500, deep_plate[well_name])
        p1000.aspirate(5, glycerol_plate[well_name])
        p1000.dispense(5, deep_plate[well_name])
        p1000.drop_tip()
        
        # Update reservoir tracking
        current_reservoir_volume -= 500
        if current_reservoir_volume <= 0:
            current_reservoir_index += 1
            current_reservoir_volume = 15000
