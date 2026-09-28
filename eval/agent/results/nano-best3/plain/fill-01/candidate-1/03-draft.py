from opentrons import protocol_api

metadata = {"protocolName": "Fill and inoculate deep well plate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    lb = protocol.define_liquid(name="lb", description="LB medium", display_color="#0000FF")
    glycerol = protocol.define_liquid(name="glycerol", description="Glycerol stock", display_color="#00FF00")
    
    # Load labware
    tip_rack_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip_rack_1000ul = protocol.load_labware("opentrons_96_tiprack_1000ul", 2)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    deep_well_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    reservoir_lb = protocol.load_labware("nest_1_reservoir_195ml", 5)
    
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack_20ul])
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tip_rack_1000ul])
    
    # Load liquids into wells
    # Load LB into reservoir well A1
    reservoir_lb["A1"].load_liquid(liquid=lb, volume=50000)  # 50 mL
    
    # Load glycerol into each well of glycerol_plate (capacity ~217 ul, so load 200 ul)
    for row in ["A","B","C","D","E","F","G","H"]:
        for col in range(1,13):
            well_name = row + str(col)
            glycerol_plate[well_name].load_liquid(liquid=glycerol, volume=200)
    
    # Fill deep well plate with 500 ul of LB per well and inoculate with 5 ul glycerol
    for row in ["A","B","C","D","E","F","G","H"]:
        for col in range(1,13):
            well_name = row + str(col)
            # Fill with LB
            p1000.pick_up_tip()
            p1000.aspirate(500, reservoir_lb["A1"])
            p1000.dispense(500, deep_well_plate[well_name])
            # Inoculate with glycerol and mix
            p20.pick_up_tip()
            p20.aspirate(5, glycerol_plate[well_name])
            p20.dispense(5, deep_well_plate[well_name])
            # Mix after glycerol addition (mix 400 ul 5 times)
            p1000.mix(400, 5, deep_well_plate[well_name])
            p1000.drop_tip()
            p20.drop_tip()
