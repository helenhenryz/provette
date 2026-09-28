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

    # helper function to do dilution series for a given stock well and row
    def dilute_antibiotic(stock_well, row_letter):
        # dilution series returns list of dicts per well
        series = dilution_series(
            stock_concentration=1,
            points=10,
            factor=2,
            final_volume_ul=50,
            first_point_is_stock=False,
            remove_excess=True
        )["wells"]
        for i, step in enumerate(series, start=1):
            col = str(i)
            dest_well = plate[f"{row_letter}{col}"]
            # step 1: add diluent (broth)
            p20.pick_up_tip()
            p20.transfer(step["step_1_add_diluent_ul"], reservoir["A1"], dest_well, new_tip='never')
            p20.drop_tip()
            # step 2: transfer antibiotic from source
            src = stock_well if i == 1 else plate[f"{row_letter}{str(i-1)}"]
            p20.pick_up_tip()
            p20.transfer(step["step_2_transfer_in_ul"], src, dest_well, new_tip='never')
            p20.drop_tip()
            # mix
            p20.pick_up_tip()
            p20.mix(3, 25, dest_well)
            p20.drop_tip()

    # dilute antibiotic 1 in row A
    dilute_antibiotic(tuberack["A1"], "A")
    # dilute antibiotic 2 in row B
    dilute_antibiotic(tuberack["A2"], "B")

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

    # optional: mix final volumes? Not required.
