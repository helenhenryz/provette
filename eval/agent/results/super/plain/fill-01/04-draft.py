import json
from opentrons import protocol_api

metadata = {"protocolName": "LB fill and glycerol inoculation", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 1)
    tips_1000_1 = protocol.load_labware("opentrons_96_tiprack_1000ul", 2)
    tips_1000_2 = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    deep_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    glycerol_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 6)

    # Pipettes
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips_1000_1, tips_1000_2])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])

    # Define liquids
    lb_liq = protocol.define_liquid(name="lb", description="LB medium", display_color="#00FF00")
    glycerol_liq = protocol.define_liquid(name="glycerol", description="Glycerol stock", display_color="#FFA500")

    # Load liquids onto deck
    reservoir["A1"].load_liquid(liquid=lb_liq, volume=195000)  # reservoir well A1
    for col in range(1, 13):
        for row in "ABCDEFGH":
            well = f"{row}{col}"
            glycerol_plate[well].load_liquid(liquid=glycerol_liq, volume=100)  # each well 100 ul

    # Fill deep well plate with 500 ul LB per well
    for col in range(1, 13):
        for row in "ABCDEFGH":
            well = f"{row}{col}"
            p1000.pick_up_tip()
            p1000.aspirate(500, reservoir["A1"])
            p1000.dispense(500, deep_plate[well])
            p1000.drop_tip()

    # Inoculate 5 ul glycerol from glycerol stock plate into matching well and mix
    for col in range(1, 13):
        for row in "ABCDEFGH":
            well = f"{row}{col}"
            p20.pick_up_tip()
            p20.aspirate(5, glycerol_plate[well])
            p20.dispense(5, deep_plate[well])
            p20.drop_tip()
            # Mix with p1000 to ensure homogeneity
            p1000.pick_up_tip()
            p1000.mix(3, 200, deep_plate[well])  # 3 strokes of 200 ul
            p1000.drop_tip()
