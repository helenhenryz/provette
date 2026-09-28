from opentrons import protocol_api

metadata = {"protocolName": "FillDeepWellPlateWithLBAndInoculate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 1)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    deep_plate = protocol.load_labware("usascientific_96_wellplate_2.4ml_deep", 3)
    tiprack_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)

    # Define liquids
    protocol.define_liquid(name="lb", description="LB medium", display_color="#0000FF")
    protocol.define_liquid(name="glycerol_stock", description="Glycerol stock", display_color="#FF0000")

    # Load liquids
    reservoir["A1"].load_liquid(liquid="lb", volume=48000)
    for well in glycerol_plate.well_names():
        glycerol_plate[well].load_liquid(liquid="glycerol_stock", volume=100)

    # Load instruments
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tiprack_1000])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack_20])

    # Fill deep well plate with 500 ul LB per well
    p1000.pick_up_tip()
    for well in deep_plate.well_names():
        p1000.aspirate(500, reservoir["A1"])
        p1000.dispense(500, deep_plate[well])
    p1000.drop_tip()

    # Inoculate each well with 5 ul from matching glycerol well
    p20.pick_up_tip()
    for well in deep_plate.well_names():
        p20.aspirate(5, glycerol_plate[well])
        p20.dispense(5, deep_plate[well])
    p20.drop_tip()
