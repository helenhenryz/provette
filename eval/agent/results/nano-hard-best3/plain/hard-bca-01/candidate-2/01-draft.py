from opentrons import protocol_api

metadata = {"protocolName": "BCA Protein Assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate_dest = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    plate_samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 4)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)

    # Define liquids
    protocol.define_liquid(name="reagent", description="BCA working reagent", display_color="#FF0000")
    protocol.define_liquid(name="bsa", description="BSA stock (2 mg/ml)", display_color="#00FF00")
    protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    for i in range(1, 41):
        protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#CCCCCC")

    # Load liquids into wells
    reagent_well = reservoir["A1"]
    reagent_well.load_liquid(liquid="reagent", volume=20000)

    bsa_well = tuberack["A1"]
    bsa_well.load_liquid(liquid="bsa", volume=1000)

    water_well = tuberack["A2"]
    water_well.load_liquid(liquid="water", volume=1000)

    sample_well_names = plate_samples.well_names[:40]
    for i, well_name in enumerate(sample_well_names, start=1):
        sample_liquid_name = f"sample {i}"
        well = plate_samples[well_name]
        well.load_liquid(liquid=sample_liquid_name, volume=200)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Get destination well lists
    all_dest_well_names = plate_dest.well_names
    sample_dest_well_names = all_dest_well_names[:80]
    standard_dest_well_names = all_dest_well_names[80:96]

    # Standard volumes (bsa, water) for each of the 16 standard wells
    standard_volumes = [
        (25, 0),   # 0
        (25, 0),   # 1
        (12.5, 12.5),  # 2
        (12.5, 12.5),  # 3
        (6.25, 18.75),  # 4
        (6.25, 18.75),  # 5
        (3.12, 21.88),  # 6
        (3.12, 21.88),  # 7
        (1.56, 23.44),  # 8
        (1.56, 23.44),  # 9
        (0.78, 24.22),  # 10
        (0.78, 24.22),  # 11
        (0.39, 24.61),  # 12
        (0.39, 24.61),  # 13
        (0, 25),  # 14
        (0, 25),  # 15
    ]

    # Process samples: each sample i (1-indexed) goes to two destination wells
    for i in range(1, 41):
        source_well_name = sample_well_names[i-1]
        source_well = plate_samples[source_well_name]
        idx = 2 * (i - 1)
        dest_well_1 = sample_dest_well_names[idx]
        dest_well_2 = sample_dest_well_names[idx + 1]
        dest_well_1_obj = plate_dest[dest_well_1]
        dest_well_2_obj = plate_dest[dest_well_2]

        # Aspirate 50 µl of sample
        p300.aspirate(50, source_well)
        # Dispense 25 µl into first destination well
        p300.dispense(25, dest_well_1_obj)
        # Dispense another 25 µl into second destination well
        p300.dispense(25, dest_well_2_obj)
        # Aspirate 200 µl reagent and dispense into first destination well
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well_1_obj)
        # Aspirate 200 µl reagent again and dispense into second destination well
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well_2_obj)
        # Drop tip
        p300.drop_tip()

    # Process standards
    for j, dest_well_name in enumerate(standard_dest_well_names):
        dest_well = plate_dest[dest_well_name]
        bsa_vol, water_vol = standard_volumes[j]
        # Pick up a tip for p20
        p20.pick_up_tip()
        # Aspirate and dispense bsa if needed
        if bsa_vol > 0:
            p20.aspirate(bsa_vol, bsa_well)
            p20.dispense(bsa_vol, dest_well)
        # Aspirate and dispense water if needed
        if water_vol > 0:
            p20.aspirate(water_vol, water_well)
            p20.dispense(water_vol, dest_well)
        # Aspirate 200 µl reagent with p300 and dispense
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well)
        # Drop tip
        p20.drop_tip()
