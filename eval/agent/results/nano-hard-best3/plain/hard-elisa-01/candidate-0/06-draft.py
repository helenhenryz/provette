from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA standard curve and samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 6)
    dest_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    dilution_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2)
    serum_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    tuberack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 5)
    
    # Define liquids
    standard_liquid = protocol.define_liquid(name="standard", description="200 ng/ml standard stock", display_color="#FF0000")
    diluent_liquid = protocol.define_liquid(name="diluent", description="Assay diluent", display_color="#0000FF")
    
    # Load serum samples
    # Hardcode the first 32 well names in the plate's order
    serum_well_names = [
        "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12",
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11", "B12",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"
    ]
    for idx, well_name in enumerate(serum_well_names):
        serum_liquid = protocol.define_liquid(name=f"serum {idx+1}", description=f"Serum sample {idx+1}", display_color="#808080")
        serum_plate[well_name].load_liquid(liquid=serum_liquid, volume=300)
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=standard_liquid, volume=1000)
    reservoir["A1"].load_liquid(liquid=diluent_liquid, volume=2000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # ==== Dilution series setup ====
    # Well 1: transfer 500 ul from standard stock into A1
    p300.pick_up_tip()
    p300.aspirate(500, tuberack["A1"])
    p300.dispense(500, dilution_plate["A1"])
    p300.mix(100, dilution_plate["A1"])
    p300.drop_tip()
    
    # Wells 2-8: add diluent, transfer from previous well, mix
    for i in range(2, 9):  # i is the well number (2 to 8)
        # Add diluent
        p300.pick_up_tip()
        p300.aspirate(250, reservoir["A1"])  # aspirate diluent
        p300.dispense(250, dilution_plate[f"A{i}"])
        # Transfer from previous well
        p300.aspirate(250, dilution_plate[f"A{i-1}"])
        p300.dispense(250, dilution_plate[f"A{i}"])
        # Mix
        p300.mix(100, dilution_plate[f"A{i}"])
        p300.drop_tip()
    
    # Remove 250 ul from the last well (A8) to waste
    p300.pick_up_tip()
    p300.aspirate(250, dilution_plate["A8"])
    p300.dispense(250, reservoir["A1"])  # dispense to waste (using reservoir well A1 as waste)
    p300.drop_tip()
    
    # ==== Prepare source wells for standards and blank ====
    # The standard source wells are A2-A8 (each will be used twice)
    # The blank well is A9 (filled with diluent only)
    blank_well = dilution_plate["A9"]
    # Fill blank well with 250 ul diluent
    p300.pick_up_tip()
    p300.aspirate(250, reservoir["A1"])
    p300.dispense(250, blank_well)
    p300.drop_tip()
    
    # Order of source wells for the 16 destination wells (standard duplicates + blank duplicates)
    source_wells = [
        dilution_plate["A2"], dilution_plate["A2"],  # 1st standard (50:50) duplicate
        dilution_plate["A3"], dilution_plate["A3"],  # 2nd standard (25:75) duplicate
        dilution_plate["A4"], dilution_plate["A4"],  # 3rd standard (12.5:87.5) duplicate
        dilution_plate["A5"], dilution_plate["A5"],  # 4th standard (6.25:93.75) duplicate
        dilution_plate["A6"], dilution_plate["A6"],  # 5th standard (3.125:96.875) duplicate
        dilution_plate["A7"], dilution_plate["A7"],  # 6th standard (1.5625:98.4375) duplicate
        dilution_plate["A8"], dilution_plate["A8"],  # 7th standard (0.78125:99.21875) duplicate
        dilution_plate["A9"],  # blank well (first replicate)
        dilution_plate["A9"]   # blank well (second replicate)
    ]
    # Get the first 16 destination well names in order
    dest_well_names = list(dest_plate)[:16]
    # Aspirate from each source well and dispense into the corresponding destination well
    for i, src_well in enumerate(source_wells):
        p300.pick_up_tip()
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_plate[dest_well_names[i]])
        p300.drop_tip()
    
    # ==== Add serum samples (32 samples, each in duplicate) ====
    # The remaining destination wells (after the first 16) are indices 16 to 79 (64 wells)
    remaining_dest_well_names = list(dest_plate)()[16:80]  # 64 wells
    # Get the first 32 serum well names (we loaded serum samples into wells with these names)
    serum_well_names = [
        "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12",
        "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11", "B12",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"
    ]
    dest_index = 0
    for src_well_name in serum_well_names:
        p300.pick_up_tip()
        p300.aspirate(100, serum_plate[src_well_name])
        # First dispense
        p300.dispense(100, dest_plate[remaining_dest_well_names[dest_index]])
        dest_index += 1
        # Second dispense (duplicate)
        p300.dispense(100, dest_plate[remaining_dest_well_names[dest_index]])
        dest_index += 1
        p300.drop_tip()
    
    # Done
