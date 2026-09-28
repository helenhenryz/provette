from opentrons import protocol_api

metadata = {"protocolName": "LB_fill_and_inoculate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 2)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    deep_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    lb = protocol.define_liquid(name="lb", description="LB medium", display_color="#0000FF")
    glycerol_stock = protocol.define_liquid(name="glycerol_stock", description="Glycerol stock", display_color="#00FF00")

    # Load liquids
    reservoir["A1"].load_liquid(liquid=lb, volume=48000)
    # Load glycerol_stock into each well of glycerol_plate
    for row in "ABCDEFGHIJ"[:8]:  # rows A-H
        for col in range(1,13):  # columns 1-12
            well_name = row + str(col)
            glycerol_plate[well_name].load_liquid(liquid=glycerol_stock, volume=100)

    # Fill deep well plate and inoculate
    for row in "ABCDEFGHIJ"[:8]:  # rows A-H
        for col in range(1,13):  # columns 1-12
            well_name = row + str(col)
            p1000.pick_up_tip()
            p1000.aspirate(500, reservoir["A1"])
            p1000.dispense(500, deep_plate[well_name])
            p1000.aspirate(5, glycerol_plate[well_name])
            p1000.dispense(5, deep_plate[well_name])
            p1000.drop_tip()
