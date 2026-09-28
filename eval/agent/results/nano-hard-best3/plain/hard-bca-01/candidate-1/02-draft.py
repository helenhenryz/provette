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

    # Load sample liquids into source plate
    for i in range(1, 41):
        if i <= 8:
            well_name = f"A{i}"
        elif i <= 16:
            well_name = f"B{i-8}"
        elif i <= 24:
            well_name = f"C{i-16}"
        elif i <= 32:
            well_name = f"D{i-24}"
        else:
            well_name = f"E{i-32}"
        source_plate.well(well_name).load_liquid(liquid=f"sample {i}", volume=100)

    # Load stock solutions
    tuberack.well("A1").load_liquid(liquid="bsa", volume=2000)      # BSA stock
    tuberack.well("B3").load_liquid(liquid="water", volume=2000)    # Water source for dilutions
    bca_reservoir.well("A1").load_liquid(liquid="reagent", volume=15000)  # BCA reagent

    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Serial dilution to prepare standards
    # Step 1: Transfer 200 µL from BSA stock (A1) to well A2
    p300.pick_up_tip()
    p300.aspirate(200, tuberack.well("A1"))
    p300.dispense(200, tuberack.well("A2"))
    p300.mix(10, 100, tuberack.well("A2"))
    p300.drop_tip()

    # Steps 2-7: Add water and transfer from previous well
    prev_well = "A2"
    for well in ["A3", "A4", "A5", "A6", "B1", "B2"]:
        p300.pick_up_tip()
        p300.aspirate(100, tuberack.well("B3"))  # water
        p300.dispense(100, tuberack.well(well))
        p300.aspirate(100, tuberack.well(prev_well))
        p300.dispense(100, tuberack.well(well))
        p300.mix(10, 100, tuberack.well(well))
        p300.drop_tip()
        prev_well = well

    # Remove 100 µL from last well (B2) to waste
    p300.pick_up_tip()
    p300.aspirate(100, tuberack.well("B2"))
    p300.dispense(100, tuberack.well("B4"))  # waste
    p300.drop_tip()

    # Define destination well order for standards (first 16 wells in column-major order)
    all_wells = []
    for col in "ABCDEFGHIJKL":
        for row in range(1, 9):
            all_wells.append(col + str(row))
    dest_std_wells = all_wells[:16]
    # Source wells for each standard entry (16 entries)
    source_wells_for_std = [
        "A2","A2","A3","A3","A4","A4","A5","A5","A6","A6","B1","B1","B2","B2","B3","B3"
    ]

    # Fill standard wells
    for i in range(16):
        p300.pick_up_tip()
        p300.aspirate(25, tuberack.well(source_wells_for_std[i]))
        p300.dispense(25, plate.well(dest_std_wells[i]))
        p300.dispense(200, bca_reservoir.well("A1"))
        p300.drop_tip()

    # Remaining wells for samples (80 wells)
    dest_sample_wells = all_wells[16:]

    # Fill sample wells (40 samples, each in duplicate)
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
        # Transfer 25 µL into two replicate wells
        for j in range(2):
            p300.pick_up_tip()
            p300.aspirate(25, source_plate.well(src_well))
            p300.dispense(25, plate.well(dest_sample_wells[2*i + j]))
            p300.dispense(200, bca_reservoir.well("A1"))
            p300.drop_tip()
