from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA standard curve and samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    standard = protocol.define_liquid(name="standard", description="200 ng/ml standard stock", display_color="#FF0000")
    diluent = protocol.define_liquid(name="diluent", description="assay diluent", display_color="#00FF00")
    for i in range(1, 33):
        protocol.define_liquid(name=f"serum {i}", description=f"Serum sample {i}", display_color=f"#{i:06X}")

    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    serum_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    dilution_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid="standard", volume=1500)
    tubes["A2"].load_liquid(liquid="diluent", volume=1500)
    
    # Generate list of the first 32 well names in the plate
    serum_well_names = []
    for col in "ABCD":
        for row in range(1, 13):
            if not (col == "D" and row > 8):
                serum_well_names.append(f"{col}{row}")
    # Load each serum sample into its well
    for i, well_name in enumerate(serum_well_names):
        well = serum_plate[well_name]
        well.load_liquid(liquid=f"serum {i+1}", volume=200)

    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Perform dilution series in intermediate plate
    series_well_names = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
    # First well: add diluent and standard
    well = dilution_plate[series_well_names[0]]
    p300.aspirate(250, tubes["A2"])  # diluent
    p300.dispense(250, well)
    p300.aspirate(250, tubes["A1"])  # standard
    p300.dispense(250, well)
    p300.mix(10, 10, well)
    
    # Subsequent wells
    for i in range(1, len(series_well_names)):
        well = dilution_plate[series_well_names[i]]
        # Add diluent
        p300.aspirate(250, tubes["A2"])
        p300.dispense(250, well)
        # Transfer from previous well
        prev_well = dilution_plate[series_well_names[i-1]]
        p300.aspirate(250, prev_well)
        p300.dispense(250, well)
        # Mix
        p300.mix(10, 10, well)
    
    # Remove 250 ul from last well to waste
    waste_tube = tubes["A3"]
    last_well = dilution_plate[series_well_names[-1]]
    p300.aspirate(250, last_well)
    p300.dispense(250, waste_tube)

    # Fill blank well with diluent only
    blank_well = dilution_plate["B1"]
    p300.aspirate(250, tubes["A2"])
    p300.dispense(250, blank_well)
    p300.mix(10, 10, blank_well)

    # Fill standard wells in dest_plate (16 wells)
    # Destination well 1: A1
    p300.aspirate(100, dilution_plate["A1"])
    p300.dispense(100, dest_plate["A1"])
    # Destination well 2: A2
    p300.aspirate(100, dilution_plate["A1"])
    p300.dispense(100, dest_plate["A2"])
    # Destination well 3: A3
    p300.aspirate(100, dilution_plate["A2"])
    p300.dispense(100, dest_plate["A3"])
    # Destination well 4: A4
    p300.aspirate(100, dilution_plate["A2"])
    p300.dispense(100, dest_plate["A4"])
    # Destination well 5: A5
    p300.aspirate(100, dilution_plate["A3"])
    p300.dispense(100, dest_plate["A5"])
    # Destination well 6: A6
    p300.aspirate(100, dilution_plate["A3"])
    p300.dispense(100, dest_plate["A6"])
    # Destination well 7: A7
    p300.aspirate(100, dilution_plate["A4"])
    p300.dispense(100, dest_plate["A7"])
    # Destination well 8: A8
    p300.aspirate(100, dilution_plate["A4"])
    p300.dispense(100, dest_plate["A8"])
    # Destination well 9: A9
    p300.aspirate(100, dilution_plate["A5"])
    p300.dispense(100, dest_plate["A9"])
    # Destination well 10: A10
    p300.aspirate(100, dilution_plate["A5"])
    p300.dispense(100, dest_plate["A10"])
    # Destination well 11: A11
    p300.aspirate(100, dilution_plate["A6"])
    p300.dispense(100, dest_plate["A11"])
    # Destination well 12: A12
    p300.aspirate(100, dilution_plate["A6"])
    p300.dispense(100, dest_plate["A12"])
    # Destination well 13: A13
    p300.aspirate(100, dilution_plate["A7"])
    p300.dispense(100, dest_plate["A13"])
    # Destination well 14: A14
    p300.aspirate(100, dilution_plate["A7"])
    p300.dispense(100, dest_plate["A14"])
    # Destination well 15: A15 (blank)
    p300.aspirate(100, blank_well)
    p300.dispense(100, dest_plate["A15"])
    # Destination well 16: A16 (blank)
    p300.aspirate(100, blank_well)
    p300.dispense(100, dest_plate["A16"])

    # Fill sample wells (64 wells) with serum samples
    # Generate all well names in order
    all_well_names = []
    for col in "ABCDEFGHI":
        for row in range(1, 13):
            all_well_names.append(f"{col}{row}")
    # The first 16 wells are used for standards
    remaining_well_names = all_well_names[16:]
    sample_well_names = remaining_well_names[:64]
    
    # Fill each serum sample into two sample wells
    for i in range(32):
        src_well = serum_plate[serum_well_names[i]]
        # Aspirate 100 ul from source well
        p300.aspirate(100, src_well)
        # Dispense into two sample wells
        p300.dispense(100, dest_plate[sample_well_names[2*i]])
        # Aspirate again
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_plate[sample_well_names[2*i+1]])

    # Drop tip
    p300.drop_tip()
