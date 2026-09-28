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
    for well in glycerol_plate.wells():
        glycerol_plate[well].load_liquid(liquid=glycerol_stock, volume=100)

    # Fill deep well plate and inoculate
    for well in deep_plate.wells():
        p1000.pick_up_tip()
        p1000.aspirate(500, reservoir["A1"])
        p1000.dispense(500, deep_plate[well])
        p1000.aspirate(5, glycerol_plate[well])
        p1000.dispense(5, deep_plate[well])
        p1000.drop_tip()
