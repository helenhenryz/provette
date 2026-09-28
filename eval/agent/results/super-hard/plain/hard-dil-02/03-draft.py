import math
from opentrons import protocol_api

metadata = {"protocolName": "1:3 serial dilution of 4 compounds", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    # assign tubes for stocks and DMSO
    comp1_stock = tuberack["A1"]  # neat stock compound 1
    comp2_stock = tuberack["B1"]  # neat stock compound 2
    comp3_stock = tuberack["C1"]  # neat stock compound 3
    comp4_stock = tuberack["D1"]  # neat stock compound 4
    dmso_tube = tuberack["A2"]    # DMSO diluent
    # dilution wells: compound 1 uses A1-A6, compound 2 B1-B6, etc.
    # assay plate
    assay_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack300])
    
    # define liquids
    comp1_liq = protocol.define_liquid(name="compound 1", description="10 mM stock", display_color="#FF0000")
    comp2_liq = protocol.define_liquid(name="compound 2", description="10 mM stock", display_color="#00FF00")
    comp3_liq = protocol.define_liquid(name="compound 3", description="10 mM stock", display_color="#0000FF")
    comp4_liq = protocol.define_liquid(name="compound 4", description="10 mM stock", display_color="#FFA500")
    dmso_liq = protocol.define_liquid(name="dmso", description="DMSO", display_color="#808080")
    medium_liq = protocol.define_liquid(name="medium", description="cell culture medium", display_color="#00FFFF")
    
    # load liquids into source tubes
    comp1_stock.load_liquid(liquid=comp1_liq, volume=500)
    comp2_stock.load_liquid(liquid=comp2_liq, volume=500)
    comp3_stock.load_liquid(liquid=comp3_liq, volume=500)
    comp4_stock.load_liquid(liquid=comp4_liq, volume=500)
    dmso_tube.load_liquid(liquid=dmso_liq, volume=1200)
    
    # pre-fill assay plate with 90 ul medium each well
    for col in range(1, 13):
        for row in "ABCDEFGH":
            well = assay_plate[f"{row}{col}"]
            well.load_liquid(liquid=medium_liq, volume=90)
    
    # helper transfers
    def transfer_p300(src, dest, vol, mix_after=False, mix_vol=0):
        p300.pick_up_tip()
        p300.aspirate(vol, src)
        p300.dispense(vol, dest)
        if mix_after:
            p300.mix(2, mix_vol, dest)
        p300.drop_tip()
    
    def transfer_p20(src, dest, vol, mix_after=False, mix_vol=0):
        p20.pick_up_tip()
        p20.aspirate(vol, src)
        p20.dispense(vol, dest)
        if mix_after:
            p20.mix(2, mix_vol, dest)
        p20.drop_tip()
    
    # serial dilution in tuberack per compound row
    rows = [("A", comp1_stock), ("B", comp2_stock), ("C", comp3_stock), ("D", comp4_stock)]
    for row_letter, stock_tube in rows:
        # point 1: 60 ul neat stock in column 1
        dest_well = tuberack[f"{row_letter}1"]
        transfer_p300(stock_tube, dest_well, 60)
        # subsequent points columns 2-6
        for col in range(2, 7):
            src_well = tuberack[f"{row_letter}{col-1}"]
            dest_well = tuberack[f"{row_letter}{col}"]
            # transfer 20 ul from previous well
            transfer_p300(src_well, dest_well, 20)
            # add 40 ul DMSO
            transfer_p300(dmso_tube, dest_well, 40, mix_after=True, mix_vol=48)  # 80% of 60ul
    
    # transfer 10 ul from each dilution point to assay plate
    for row_letter in ["A","B","C","D"]:
        for col in range(1, 7):
            src_well = tuberack[f"{row_letter}{col}"]
            dest_well = assay_plate[f"{row_letter}{col}"]
            transfer_p20(src_well, dest_well, 10, mix_after=True, mix_vol=20)  # max p20 volume
