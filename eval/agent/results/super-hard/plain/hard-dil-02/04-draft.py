import math
from opentrons import protocol_api

metadata = {"protocolName": "1:3 serial dilution of 4 compounds", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    dilution_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    assay_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 6)
    # stocks and DMSO
    comp1_stock = tuberack["A1"]
    comp2_stock = tuberack["B1"]
    comp3_stock = tuberack["C1"]
    comp4_stock = tuberack["D1"]
    dmso_tube = tuberack["A2"]
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
    
    # helper transfers with mixing
    def transfer_p300(src, dest, vol, mix_after=False, mix_vol=0, mix_reps=2):
        p300.pick_up_tip()
        p300.aspirate(vol, src)
        p300.dispense(vol, dest)
        if mix_after:
            p300.mix(mix_reps, mix_vol, dest)
        p300.drop_tip()
    
    def transfer_p20(src, dest, vol, mix_after=False, mix_vol=0, mix_reps=2):
        p20.pick_up_tip()
        p20.aspirate(vol, src)
        p20.dispense(vol, dest)
        if mix_after:
            p20.mix(mix_reps, mix_vol, dest)
        p20.drop_tip()
    
    # serial dilution in dilution plate per compound row
    rows = [("A", comp1_stock), ("B", comp2_stock), ("C", comp3_stock), ("D", comp4_stock)]
    for row_letter, stock_tube in rows:
        # point 1: 60 ul neat stock
        dest_well = dilution_plate[f"{row_letter}1"]
        transfer_p300(stock_tube, dest_well, 60, mix_after=True, mix_vol=48, mix_reps=5)  # 80% of 60ul
        # subsequent points
        for col in range(2, 7):
            src_well = dilution_plate[f"{row_letter}{col-1}"]
            dest_well = dilution_plate[f"{row_letter}{col}"]
            # transfer 20 ul from previous well
            transfer_p300(src_well, dest_well, 20, mix_after=False)
            # add 40 ul DMSO
            transfer_p300(dmso_tube, dest_well, 40, mix_after=True, mix_vol=48, mix_reps=5)
    
    # transfer 10 ul from each dilution point to assay plate
    for row_letter in ["A","B","C","D"]:
        for col in range(1, 7):
            src_well = dilution_plate[f"{row_letter}{col}"]
            dest_well = assay_plate[f"{row_letter}{col}"]
            transfer_p20(src_well, dest_well, 10, mix_after=True, mix_vol=20, mix_reps=5)  # max p20 vol
    
    # optional: add DMSO-only wells as blank (column 7) for each row
    for row_letter in ["A","B","C","D"]:
        blank_well = dilution_plate[f"{row_letter}7"]
        transfer_p300(dmso_tube, blank_well, 60, mix_after=True, mix_vol=48, mix_reps=5)
