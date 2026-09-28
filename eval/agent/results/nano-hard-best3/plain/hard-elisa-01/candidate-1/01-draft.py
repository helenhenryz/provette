from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA Standard Curve",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    source_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])
    
    # Define liquids
    standard_liquid = protocol.define_liquid(
        name="standard", description="200 ng/ml standard stock", display_color="#FF0000"
    )
    diluent_liquid = protocol.define_liquid(
        name="diluent", description="assay diluent", display_color="#00FF00"
    )
    serum_liquids = {}
    for i in range(1, 33):
        serum_liquids[i] = protocol.define_liquid(
            name=f"serum {i}", description=f"Serum sample {i}", display_color="#0000FF"
        )
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=standard_liquid, volume=500)
    tuberack["A2"].load_liquid(liquid=diluent_liquid, volume=1700)
    for i in range(1, 33):
        source_plate[f"B{i}"].load_liquid(liquid=serum_liquids[i], volume=300)
    
    # Perform dilution series in source_plate column A wells A1-A7
    # Step 1: Transfer 500 µL of standard from tuberack["A1"] to source_plate["A1"]
    p300.pick_up_tip()
    p300.aspirate(500, tuberack["A1"])
    p300.dispense(500, source_plate["A1"])
    p300.drop_tip()
    
    # Step 2-7: For each of the next 6 wells (A2-A7), add 250 µL diluent, then transfer 250 µL from previous well
    for i in range(2, 8):  # i = 2,3,4,5,6,7
        # Add 250 µL diluent to well A{i}
        p300.pick_up_tip()
        p300.aspirate(250, tuberack["A2"])
        p300.dispense(250, source_plate[f"A{i}"])
        # Transfer 250 µL from previous well (A{i-1}) to current well A{i}
        p300.aspirate(250, source_plate[f"A{i-1}"])
        p300.dispense(250, source_plate[f"A{i}"])
        # Mix after transfer
        p300.mix(2, 250, source_plate[f"A{i}"])
        p300.drop_tip()
    
    # Step 8: Remove 250 µL from the last well (A7) to waste
    p300.pick_up_tip()
    p300.aspirate(250, source_plate["A7"])
    p300.drop_tip()
    
    # Load blank well A8 with remaining diluent (200 µL)
    p300.pick_up_tip()
    p300.aspirate(200, tuberack["A2"])
    p300.dispense(200, source_plate["A8"])
    p300.drop_tip()
    
    # Generate list of all 96 wells in order (A1..H12)
    rows = "ABCDEFGHI"
    dest_well_names = []
    for row in rows:
        for col in range(1, 13):
            dest_well_names.append(f"{row}{col}")
    
    # Fill standards and blank (16 wells total)
    # Each standard point dispensed in duplicate
    for i in range(7):
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[f"A{i+1}"])
        p300.dispense(100, plate[dest_well_names[2*i]])
        p300.dispense(100, plate[dest_well_names[2*i+1]])
        p300.drop_tip()
    
    # Fill blank (wells 15 and 16, indices 14 and 15)
    p300.pick_up_tip()
    p300.aspirate(100, source_plate["A8"])
    p300.dispense(100, plate[dest_well_names[14]])
    p300.dispense(100, plate[dest_well_names[15]])
    p300.drop_tip()
    
    # Fill serum samples (32 samples, each in duplicate)
    for i in range(32):
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[f"B{i+1}"])
        p300.dispense(100, plate[dest_well_names[16 + 2*i]])
        p300.dispense(100, plate[dest_well_names[16 + 2*i + 1]])
        p300.drop_tip()
