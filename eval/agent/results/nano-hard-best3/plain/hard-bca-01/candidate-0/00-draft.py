from opentrons import protocol_api

metadata = {
    "protocolName": "BCA Protein Assay",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    destination_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 3)
    reagent_reservoir = protocol.load_labware("nest_1_reservoir_195ml", 4)
    bsa_tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)
    
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    reagent = protocol.define_liquid(name="reagent", description="BCA working reagent", display_color="#0000FF")
    bsa = protocol.define_liquid(name="bsa", description="BSA stock (2 mg/mL)", display_color="#000000")
    water = protocol.define_liquid(name="water", description="Water", display_color="#FFFFFF")
    for i in range(1, 41):
        protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#808080")
    
    # Load liquids into source wells
    # Load reagent into reservoir well A1
    reagent_reservoir["A1"].load_liquid(reagent, volume=20000)
    # Load bsa into tube rack well A1
    bsa_tuberack["A1"].load_liquid(bsa, volume=1000)
    # Load water into reservoir well A2
    reagent_reservoir["A2"].load_liquid(water, volume=10000)
    # Load samples into source plate wells A1 through D4
    sample_well_ids = []
    # A1-A12
    for col in range(1, 13):
        sample_well_ids.append(f"A{col}")
    # B1-B12
    for col in range(1, 13):
        sample_well_ids.append(f"B{col}")
    # C1-C12
    for col in range(1, 13):
        sample_well_ids.append(f"C{col}")
    # D1-D4
    for col in range(1, 5):
        sample_well_ids.append(f"D{col}")
    # Load each sample
    for i, well_id in enumerate(sample_well_ids):
        source_plate[well_id].load_liquid(liquid=f"sample {i+1}", volume=300)
    
    # Generate destination well IDs for samples (first 80 wells)
    dest_well_ids = []
    # A1-A12
    for col in range(1, 13):
        dest_well_ids.append(f"A{col}")
    # B1-B12
    for col in range(1, 13):
        dest_well_ids.append(f"B{col}")
    # C1-C12
    for col in range(1, 13):
        dest_well_ids.append(f"C{col}")
    # D1-D12
    for col in range(1, 13):
        dest_well_ids.append(f"D{col}")
    # E1-E12
    for col in range(1, 13):
        dest_well_ids.append(f"E{col}")
    # F1-F12
    for col in range(1, 13):
        dest_well_ids.append(f"F{col}")
    # G1-G8
    for col in range(1, 9):
        dest_well_ids.append(f"G{col}")
    
    # Transfer samples (25 ul each) to two destination wells each
    for i in range(len(sample_well_ids)):
        p300.pick_up_tip()
        src_well = source_plate[sample_well_ids[i]]
        p300.aspirate(25, src_well)
        # Dispense into two destination wells
        dest_well_1 = destination_plate[dest_well_ids[2*i]]
        dest_well_2 = destination_plate[dest_well_ids[2*i+1]]
        p300.dispense(25, dest_well_1)
        p300.dispense(25, dest_well_2)
        p300.drop_tip()
    
    # Standard curve compositions
    standard_compositions = [
        {"bsa_ul": 25, "water_ul": 0},
        {"bsa_ul": 25, "water_ul": 0},
        {"bsa_ul": 12.5, "water_ul": 12.5},
        {"bsa_ul": 12.5, "water_ul": 12.5},
        {"bsa_ul": 6.25, "water_ul": 18.75},
        {"bsa_ul": 6.25, "water_ul": 18.75},
        {"bsa_ul": 3.12, "water_ul": 21.88},
        {"bsa_ul": 3.12, "water_ul": 21.88},
        {"bsa_ul": 1.56, "water_ul": 23.44},
        {"bsa_ul": 1.56, "water_ul": 23.44},
        {"bsa_ul": 0.78, "water_ul": 24.22},
        {"bsa_ul": 0.78, "water_ul": 24.22},
        {"bsa_ul": 0.39, "water_ul": 24.61},
        {"bsa_ul": 0.39, "water_ul": 24.61},
        {"bsa_ul": 0, "water_ul": 25},
        {"bsa_ul": 0, "water_ul": 25}
    ]
    
    # Fill standard curve wells
    standard_well_ids = [
        "G9","G10","G11","G12","H1","H2","H3","H4","H5","H6","H7","H8","H9","H10","H11","H12"
    ]
    for i, well_id in enumerate(standard_well_ids):
        comp = standard_compositions[i]
        p300.pick_up_tip()
        if comp["bsa_ul"] > 0:
            p300.aspirate(comp["bsa_ul"], bsa_tuberack["A1"])
        if comp["water_ul"] > 0:
            p300.aspirate(comp["water_ul"], reagent_reservoir["A2"])
        if comp["bsa_ul"] > 0:
            p300.dispense(comp["bsa_ul"], destination_plate[well_id])
        if comp["water_ul"] > 0:
            p300.dispense(comp["water_ul"], destination_plate[well_id])
        p300.drop_tip()
    
    # Add 200 ul reagent to every well
    for well in destination_plate.wells():
        p300.pick_up_tip()
        p300.aspirate(200, reagent_reservoir["A1"])
        p300.dispense(200, well)
        p300.drop_tip()
