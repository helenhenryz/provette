import math
from opentrons import protocol_api

metadata = {"protocolName": "ELISA standard curve and samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    dilution_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    sample_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    elisa_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 6)
    
    # ----- Pipette -----
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # ----- Liquids -----
    standard = protocol.define_liquid(name="standard", description="200 ng/ml ELISA standard", display_color="#FF0000")
    diluent = protocol.define_liquid(name="diluent", description="Assay diluent", display_color="#00FF00")
    # define serums
    serums = []
    for i in range(1, 33):
        name = f"serum {i}"
        liq = protocol.define_liquid(name=name, description=f"Pre‑diluted serum sample {i}", display_color="#0000FF")
        serums.append(liq)
    
    # Load liquids into wells
    tube_rack["A1"].load_liquid(liquid=standard, volume=600)   # standard stock
    tube_rack["A2"].load_liquid(liquid=diluent, volume=2000)  # diluent
    
    for idx, well in enumerate(sample_plate.wells[:32]):
        well.load_liquid(liquid=serums[idx], volume=250)
    
    # ----- Step 1: Prepare 1:2 dilution series (7 points, 250 ul each) -----
    # Use the dilution_series tool logic manually
    stock_well = tube_rack["A1"]
    diluent_well = tube_rack["A2"]
    # We'll track previous well for transfers
    prev_well = None
    for i, well in enumerate(dilution_plate.wells[:7]):  # wells 1-7
        p300.pick_up_tip()
        if i == 0:
            # Step 1: add diluent (0 ul) -> none
            # Step 2: transfer 500 ul stock
            p300.aspirate(500, stock_well)
            p300.dispense(500, well)
        else:
            # Step 1: add 250 ul diluent
            p300.aspirate(250, diluent_well)
            p300.dispense(250, well)
            # Step 2: transfer 250 ul from previous well
            p300.aspirate(250, prev_well)
            p300.dispense(250, well)
        # Mix 3 times 150 ul
        p300.mix(3, 150, well)
        p300.drop_tip()
        prev_well = well
    # Remove excess from last well (250 ul) to waste (just discard tip)
    p300.pick_up_tip()
    p300.aspirate(250, dilution_plate.wells[6])
    p300.dispense(250, tube_rack["A1"])  # optional back to stock or just blow out; we'll just blow out
    p300.blow_out(tube_rack["A1"])
    p300.drop_tip()
    
    # ----- Step 2: Transfer standards (duplicate) to ELISA plate -----
    # Standards wells 0-6 correspond to rows A-G, columns 1 and 2
    for i, std_well in enumerate(dilution_plate.wells[:7]):
        row = chr(ord('A') + i)
        dest1 = elisa_plate[f"{row}1"]
        dest2 = elisa_plate[f"{row}2"]
        for dest in (dest1, dest2):
            p300.pick_up_tip()
            p300.aspirate(100, std_well)
            p300.dispense(100, dest)
            p300.drop_tip()
    # Blank duplicates (diluent only) in row H, columns 1 and 2
    blank_row = "H"
    for col in ("1", "2"):
        dest = elisa_plate[f"{blank_row}{col}"]
        p300.pick_up_tip()
        p300.aspirate(100, diluent_well)
        p300.dispense(100, dest)
        p300.drop_tip()
    
    # ----- Step 3: Transfer samples (duplicate) to ELISA plate -----
    # Use columns 3-12, two columns per row block
    sample_idx = 0
    for col_start in range(3, 13, 2):  # 3,5,7,9,11
        for row_letter in ["A","B","C","D","E","F","G","H"]:
            if sample_idx >= 32:
                break
            src = sample_plate.wells[sample_idx]
            dest1 = elisa_plate[f"{row_letter}{col_start}"]
            dest2 = elisa_plate[f"{row_letter}{col_start+1}"]
            for dest in (dest1, dest2):
                p300.pick_up_tip()
                p300.aspirate(100, src)
                p300.dispense(100, dest)
                p300.drop_tip()
            sample_idx += 1
        if sample_idx >= 32:
            break
