from opentrons import protocol_api

metadata = {"protocolName": "BCA Protein Assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    bca_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Define liquids
    protocol.define_liquid("reagent", description="BCA working reagent", display_color="#FF0000")
    protocol.define_liquid("bsa", description="BSA stock (2 mg/ml)", display_color="#00FF00")
    protocol.define_liquid("water", description="Water (nuclease-free)", display_color="#0000FF")
    for i in range(1, 41):
        protocol.define_liquid(f"sample {i}", description=f"Protein sample {i}", display_color="#808080")

    # Load liquids
    # Load samples into source plate
    for i in range(1, 41):
        well_name = f"A{i}" if i <= 8 else f"B{i-8}" if i <= 16 else f"C{i-16}" if i <= 24 else f"D{i-24}" if i <= 32 else f"E{i-32}"
        source_plate.well(well_name).load_liquid(liquid=f"sample {i}", volume=100)

    # Load BSA stock into tuberack well A1
    tuberack.well("A1").load_liquid(liquid="bsa", volume=2000)
    # Load water into tuberack well A9 (also used as blank source)
    tuberack.well("A9").load_liquid(liquid="water", volume=2000)
    # Load reagent into reservoir well A1
    bca_reservoir.well("A1").load_liquid(liquid="reagent", volume=15000)

    # Perform serial dilution to prepare standards
    # Step 1: Transfer 200 µL from BSA stock (A1) to well A2
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300.pick_up_tip()
    p300.aspirate(200, tuberack.well("A1"))
    p300.dispense(200, tuberack.well("A2"))
    p300.mix(10, 100, tuberack.well("A2"))
    p300.drop_tip()

    # Step 2: For wells A3-A8, add 100 µL water and transfer 100 µL from previous well
    for i in range(3, 9):
        p300.pick_up_tip()
        p300.aspirate(100, tuberack.well("A9"))  # water source
        p300.dispense(100, tuberack.well(f"A{i}"))
        p300.aspirate(100, tuberack.well(f"A{i-1}"))
        p300.dispense(100, tuberack.well(f"A{i}"))
        p300.mix(10, 100, tuberack.well(f"A{i}"))
        p300.drop_tip()

    # Remove 100 µL from last well (A8) to waste
    p300.pick_up_tip()
    p300.aspirate(100, tuberack.well("A8"))
    p300.dispense(100, tuberack.well("A10"))  # waste well
    p300.drop_tip()

    # Define destination well order for standards (first 16 wells in column-major order)
    dest_std_wells = ["A1","A2","A3","A4","A5","A6","A7","A8","B1","B2","B3","B4","B5","B6","B7","B8"]
    # Source wells for each standard entry (16 entries)
    source_wells_for_std = [
        "A2","A2","A3","A3","A4","A4","A5","A5","A6","A6","A7","A7","A8","A8","A9","A9"
    ]

    # Fill standard wells
    for i in range(16):
        p300.pick_up_tip()
        p300.aspirate(25, tuberack.well(source_wells_for_std[i]))
        p300.dispense(25, plate.well(dest_std_wells[i]))
        p300.dispense(200, bca_reservoir.well("A1"))
        p300.drop_tip()

    # Generate list of all destination wells in column-major order
    all_wells = []
    for col in "ABCDEFGHIJKL":
        for row in range(1, 9):
            all_wells.append(col + str(row))
    dest_sample_wells = all_wells[16:]  # remaining 80 wells

    # Fill sample wells (80 wells, 40 samples each in duplicate)
    for i in range(40):
        # Determine source plate well for sample i+1
        s = i + 1
        if s <= 8:
            src_well = f"A{s}"
        elif s <= 16:
            src_well = f"B{s-8}"
        elif s <= 24:
            src_well = f"C{s-16}"
        elif s <= 32:
            src_well = f"D{s-24}"
        else:
            src_well = f"E{s-32}"
        # Load 25 µL into two replicate wells
        for j in range(2):
            p300.pick_up_tip()
            p300.aspirate(25, source_plate.well(src_well))
            p300.dispense(25, plate.well(dest_sample_wells[2*i + j]))
            p300.dispense(200, bca_reservoir.well("A1"))
            p300.drop_tip()

submit()
