import math
from opentrons import protocol_api

metadata = {"protocolName": "MIC plate for 2 antibiotics", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    # define liquids
    antibiotic1 = protocol.define_liquid(name="antibiotic 1", description="antibiotic stock", display_color="#FF0000")
    antibiotic2 = protocol.define_liquid(name="antibiotic 2", description="antibiotic stock", display_color="#00FF00")
    broth = protocol.define_liquid(name="broth", description="Mueller-Hinton broth", display_color="#0000FF")
    culture = protocol.define_liquid(name="culture", description="bacterial culture", display_color="#FFA500")

    # load liquids into sources
    tuberack["A1"].load_liquid(liquid=antibiotic1, volume=1500)  # antibiotic 1 stock
    tuberack["A2"].load_liquid(liquid=antibiotic2, volume=1500)  # antibiotic 2 stock
    tuberack["A3"].load_liquid(liquid=culture, volume=1500)      # culture
    reservoir["A1"].load_liquid(liquid=broth, volume=15000)     # broth reservoir

    # perform serial dilution for each antibiotic in rows A and B
    # Each well: add 50 µL broth, then transfer 50 µL antibiotic from source (stock or previous well)
    for row, stock_well in [("A", tuberack["A1"]), ("B", tuberack["A2"])]:
        for col in range(1, 11):  # columns 1-10
            dest = plate[f"{row}{col}"]
            # step 1: add broth
            p300.pick_up_tip()
            p300.transfer(50, reservoir["A1"], dest, new_tip='never')
            p300.drop_tip()
            # step 2: transfer antibiotic
            src = stock_well if col == 1 else plate[f"{row}{col-1}"]
            p300.pick_up_tip()
            p300.transfer(50, src, dest, new_tip='never')
            p300.drop_tip()
            # mix
            p20.pick_up_tip()
            p20.mix(3, 20, dest)
            p20.drop_tip()
        # after finishing the row, remove excess 50 µL from column 10 to waste
        last_well = plate[f"{row}10"]
        p300.pick_up_tip()
        p300.aspirate(50, last_well)
        p300.drop_tip()  # discarding to trash
        # add broth to column 11 (growth control)
        growth_well = plate[f"{row}11"]
        p300.pick_up_tip()
        p300.transfer(50, reservoir["A1"], growth_well, new_tip='never')
        p300.drop_tip()

    # add culture to columns 1-11 rows A and B
    for row in ["A", "B"]:
        for col in range(1, 12):  # 1 to 11
            well = plate[f"{row}{col}"]
            p300.pick_up_tip()
            p300.transfer(50, tuberack["A3"], well, new_tip='never')
            p300.drop_tip()

    # add broth alone to column 12 rows A and B (sterility control)
    for row in ["A", "B"]:
        well = plate[f"{row}12"]
        p300.pick_up_tip()
        p300.transfer(100, reservoir["A1"], well, new_tip='never')
        p300.drop_tip()
