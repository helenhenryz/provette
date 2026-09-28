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

    # Define liquids and capture return values
    reagent_liquid = protocol.define_liquid(name="reagent", description="BCA working reagent", display_color="#FF0000")
    bsa_liquid = protocol.define_liquid(name="bsa", description="BSA stock (2 mg/ml)", display_color="#00FF00")
    water_liquid = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    sample_liquids = {}
    for i in range(1, 41):
        sample_liquids[i] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#CCCCCC")

    # Load liquids into wells
    reagent_well = reservoir["A1"]
    reagent_well.load_liquid(liquid=reagent_liquid, volume=20000)

    bsa_well = tuberack["A1"]
    bsa_well.load_liquid(liquid=bsa_liquid, volume=1000)

    water_well = tuberack["A2"]
    water_well.load_liquid(liquid=water_liquid, volume=1000)

    # Generate well names in column‑major order for source plate
    sample_well_names = []
    for col in "ABCDEFGHIJKL":
        for row in range(1, 13):
            sample_well_names.append(col + str(row))
    sample_well_names = sample_well_names[:40]

    # Load sample liquids into source plate wells
    for idx, well_name in enumerate(sample_well_names, start=1):
        well = plate_samples[well_name]
        well.load_liquid(liquid=sample_liquids[idx], volume=200)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Generate well names in column‑major order for destination plate
    all_dest_well_names = []
    for col in "ABCDEFGHIJKL":
        for row in range(1, 13):
            all_dest_well_names.append(col + str(row))

    # Split destination wells into samples and standards
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

    # Process samples: each sample i (1‑indexed) goes to two destination wells
    for i in range(1, 41):
        # Pick up a tip for p300
        p300.pick_up_tip()
        source_well_name = sample_well_names[i-1]
        source_well = plate_samples[source_well_name]
        idx = 2 * (i - 1)
        dest_well_1 = sample_dest_well_names[idx]
        dest_well_2 = sample_dest_well_names[idx + 1]
        dest_well_1_obj = plate_dest[dest_well_1]
        dest_well_2_obj = plate_dest[dest_well_2]

        # Aspirate 50 µl of sample
        p300.aspirate(50, source_well)
        # Dispense 25 µl into first destination well
        p300.dispense(25, dest_well_1_obj)
        # Dispense another 25 µl into second destination well
        p300.dispense(25, dest_well_2_obj)
        # Aspirate 200 µl reagent and dispense into first destination well
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well_1_obj)
        # Aspirate 200 µl reagent again and dispense into second destination well
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well_2_obj)
        # Drop tip
        p300.drop_tip()

    # Process standards
    for j, dest_well_name in enumerate(standard_dest_well_names):
        dest_well = plate_dest[dest_well_name]
        bsa_vol, water_vol = standard_volumes[j]
        # Handle bsa_vol
        if bsa_vol > 0:
            if bsa_vol <= 20:
                pipette = p20
            else:
                pipette = p300
            pipette.pick_up_tip()
            pipette.aspirate(bsa_vol, bsa_well)
            pipette.dispense(bsa_vol, dest_well)
            pipette.drop_tip()
        # Handle water_vol
        if water_vol > 0:
            if water_vol <= 20:
                pipette = p20
            else:
                pipette = p300
            pipette.pick_up_tip()
            pipette.aspirate(water_vol, water_well)
            pipette.dispense(water_vol, dest_well)
            pipette.drop_tip()
        # Aspirate 200 µl reagent with p300 and dispense
        p300.pick_up_tip()
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, dest_well)
        p300.drop_tip()
