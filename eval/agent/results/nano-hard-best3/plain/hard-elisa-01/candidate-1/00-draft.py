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
    protocol.define_liquid(name="standard", description="200 ng/ml standard stock", display_color="#FF0000")
    protocol.define_liquid(name="diluent", description="assay diluent", display_color="#00FF00")
    for i in range(1, 33):
        protocol.define_liquid(name=f"serum {i}", description=f"Serum sample {i}", display_color="#0000FF")
    
    # Load liquids into source wells
    # Load 500 µL of standard into tube A1 of tuberack
    tuberack["A1"].load_liquid(liquid="standard", volume=500)
    # Load 1700 µL of diluent into tube A2 of tuberack (1500 for series + 200 for blank)
    tuberack["A2"].load_liquid(liquid="diluent", volume=1700)
    # Load serum samples into source_plate column B (B1-B32)
    for i in range(1, 33):
        source_plate[f"B{i}"].load_liquid(liquid=f"serum {i}", volume=300)
    
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
    
    # Generate list of all 96 wells in order
    rows = "ABCDEFGHI"
    dest_well_names = []
    for row in rows:
        for col in range(1, 13):
            dest_well_names.append(f"{row}{col}")
    
    # Fill standards and blank
    # For each of the 7 standard points (A1-A7), dispense 100 µL into two destination wells
    for i in range(7):
        # Source well is A{i+1}
        # Destination wells are dest_well_names[2*i] and dest_well_names[2*i+1]
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[f"A{i+1}"])
        p300.dispense(100, plate[dest_well_names[2*i]])
        p300.dispense(100, plate[dest_well_names[2*i+1]])
        p300.drop_tip()
    
    # Fill blank: aspirate from source_plate["A8"] and dispense into dest_well_names[14] and dest_well_names[15]
    p300.pick_up_tip()
    p300.aspirate(100, source_plate["A8"])
    p300.dispense(100, plate[dest_well_names[14]])
    p300.dispense(100, plate[dest_well_names[15]])
    p300.drop_tip()
    
    # Fill serum samples: for each serum i (1 to 32), aspirate from source_plate["B{i}"] and dispense into two destination wells
    for i in range(32):
        # Source well is source_plate[f"B{i+1}"]
        # Destination wells are dest_well_names[16 + 2*i] and dest_well_names[16 + 2*i + 1]
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[f"B{i+1}"])
        p300.dispense(100, plate[dest_well_names[16 + 2*i]])
        p300.dispense(100, plate[dest_well_names[16 + 2*i + 1]])
        p300.drop_tip()
