from opentrons import protocol_api

metadata = {
    "protocolName": "Fill Deep Well Plate with LB and Inoculate with Glycerol Stock",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    lb = protocol.define_liquid(name="lb", description="LB medium", display_color="#0000FF")
    glycerol_stock = protocol.define_liquid(name="glycerol_stock", description="Glycerol stock", display_color="#FF0000")
    
    # Load labware
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", "1")
    deep_well_plate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", "2")
    glycerol_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "3")
    
    # Load tip racks
    tip_rack_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", "4")
    tip_rack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", "6")
    
    # Load instruments
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tip_rack_1000])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack_300])
    
    # Load LB into reservoir
    reservoir["A1"].load_liquid(liquid=lb, volume=50000)
    
    # Load glycerol stock into each well of glycerol plate
    for well in glycerol_plate.wells():
        well.load_liquid(liquid=glycerol_stock, volume=50)
    
    # Fill deep well plate with 500 ul LB per well
    for well in deep_well_plate.wells():
        p1000.pick_up_tip()
        p1000.aspirate(500, reservoir["A1"])
        p1000.dispense(500, well)
        p1000.drop_tip()
    
    # Inoculate each well with 5 ul glycerol stock and mix
    for deep_well, glycerol_well in zip(deep_well_plate.wells(), glycerol_plate.wells()):
        p300.pick_up_tip()
        p300.aspirate(20, glycerol_well)
        p300.dispense(5, deep_well)
        p300.mix(300, 5, deep_well)
        p300.drop_tip()
