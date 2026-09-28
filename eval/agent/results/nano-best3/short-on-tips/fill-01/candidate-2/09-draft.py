from opentrons import protocol_api

metadata = {
    "protocolName": "Fill and inoculate 96-well deep well plate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 1)
    deep_well_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 2)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p1000_tiprack = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)
    p300_tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[p1000_tiprack])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[p300_tiprack])
    
    # Define LB liquid
    lb = protocol.define_liquid(
        name="lb",
        description="LB medium",
        display_color="#0000FF"
    )
    # Load LB into reservoir well A1
    reservoir["A1"].load_liquid(liquid=lb, volume=48000)
    
    # Generate well names for 96-well plate (A1..H12)
    well_names = []
    for row in "ABCDEFGH":
        for col in range(1,13):
            well_names.append(row + str(col))
    
    # Define source liquids for each well of glycerol plate and load them
    for well_name in well_names:
        well = glycerol_plate[well_name]
        # Define a unique liquid for each well
        liquid_name = f"source_{well_name}"
        src_liquid = protocol.define_liquid(
            name=liquid_name,
            description=f"Glycerol stock {well_name}",
            display_color="#000000"
        )
        # Load a realistic starting volume, e.g., 100 µL
        well.load_liquid(liquid=src_liquid, volume=100)
    
    # Fill deep well plate with 500 µL LB per well
    p1000.pick_up_tip()
    for well in deep_well_plate.wells():
        p1000.aspirate(500, reservoir["A1"])
        p1000.dispense(500, well)
    p1000.drop_tip()
    
    # Inoculate each well with 5 µL from matching well of glycerol plate
    dest_wells = list(deep_well_plate.wells())
    for well_name, dest_well in zip(well_names, dest_wells):
        p300.pick_up_tip()
        src_well = glycerol_plate[well_name]
        p300.aspirate(20, src_well)
        p300.dispense(5, dest_well)
        # Mix using p1000
        p1000.pick_up_tip()
        p1000.aspirate(300, dest_well)
        p1000.mix(5, 300, dest_well)
        p1000.drop_tip()
        p300.drop_tip()
