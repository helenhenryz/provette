import math
from opentrons import protocol_api

metadata = {"protocolName": "ELISA standard curve and samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)  # for standard stock
    diluent_rack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 2)  # same slot? Can't have two in same slot. We'll put diluent in slot 7 actually.
    # Let's reorganize: slot 2 tube rack for standard, slot 3 tips, slot 4 dilution plate, slot 5 sample plate, slot 6 ELISA plate, slot 7 diluent tube rack
    # Actually we need to adjust slots: we'll put standard tube rack in slot 2, diluent tube rack in slot 7, tips slot 3, dilution plate slot 4, sample plate slot 5, ELISA plate slot 6.
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    diluent_rack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 7)
    dilution_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    sample_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    elisa_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 6)
    
    # ----- Pipette -----
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips])
    
    # ----- Liquids -----
    standard = protocol.define_liquid(name="standard", description="200 ng/ml ELISA standard", display_color="#FF0000")
    diluent = protocol.define_liquid(name="diluent", description="Assay diluent", display_color="#00FF00")
    serums = []
    for i in range(1, 33):
        name = f"serum {i}"
        liq = protocol.define_liquid(name=name, description=f"Pre‑diluted serum sample {i}", display_color="#0000FF")
        serums.append(liq)
    
    # Load liquids into wells
    tube_rack["A1"].load_liquid(liquid=standard, volume=600)   # standard stock
    diluent_rack["A1"].load_liquid(liquid=diluent, volume=2000)  # diluent
    
    for idx, well in enumerate(sample_plate.wells()[:32]):
        well.load_liquid(liquid=serums[idx], volume=250)
    
    # ----- Step 1: Prepare 1:2 dilution series (7 points, 250 ul each) plus blank -----
    stock_well = tube_rack["A1"]
    diluent_well = diluent_rack["A1"]
    prev_well = None
    # Points 1-7
    for i, well in enumerate(dilution_plate.wells()[:7]):  # wells A1-G1
        p1000.pick_up_tip()
        if i == 0:
            # transfer 500 ul stock
            p1000.aspirate(500, stock_well)
            p1000.dispense(500, well)
        else:
            # add 250 ul diluent
            p1000.aspirate(250, diluent_well)
            p1000.dispense(250, well)
            # transfer 250 ul from previous well
            p1000.aspirate(250, prev_well)
            p1000.dispense(250, well)
        # Mix 5 times 400 ul (80% of 500ul approx)
        p1000.mix(5, 400, well)
        p1000.drop_tip()
        prev_well = well
    # Blank well (diluent only) at H1 (well index 7)
    blank_well = dilution_plate.wells()[7]
    p1000.pick_up_tip()
    p1000.aspirate(250, diluent_well)
    p1000.dispense(250, blank_well)
    p1000.mix(3, 150, blank_well)  # small mix ok
    p1000.drop_tip()
    
    # ----- Step 2: Transfer standards (duplicate) to ELISA plate -----
    # Standards wells 0-6 correspond to rows A-G, columns 1 and 2
    for i, std_well in enumerate(dilution_plate.wells()[:7]):
        row = chr(ord('A') + i)
        dest1 = elisa_plate[f"{row}1"]
        dest2 = elisa_plate[f"{row}2"]
        for dest in (dest1, dest2):
            p1000.pick_up_tip()
            p1000.aspirate(100, std_well)
            p1000.dispense(100, dest)
            p1000.drop_tip()
    # Blank duplicates (diluent only) from blank_well to row H, columns 1 and 2
    blank_row = "H"
    for col in ("1", "2"):
        dest = elisa_plate[f"{blank_row}{col}"]
        p1000.pick_up_tip()
        p1000.aspirate(100, blank_well)
        p1000.dispense(100, dest)
        p1000.drop_tip()
    
    # ----- Step 3: Transfer samples (duplicate) to ELISA plate -----
    sample_idx = 0
    for col_start in range(3, 13, 2):  # 3,5,7,9,11
        for row_letter in ["A","B","C","D","E","F","G","H"]:
            if sample_idx >= 32:
                break
            src = sample_plate.wells()[sample_idx]
            dest1 = elisa_plate[f"{row_letter}{col_start}"]
            dest2 = elisa_plate[f"{row_letter}{col_start+1}"]
            for dest in (dest1, dest2):
                p1000.pick_up_tip()
                p1000.aspirate(100, src)
                p1000.dispense(100, dest)
                p1000.drop_tip()
            sample_idx += 1
        if sample_idx >= 32:
            break
