from opentrons import protocol_api

metadata = {"protocolName": "Normalize DNA samples to 10 ng/ul in 50 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    # Tip racks
    p20_tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p300_tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    # Plates
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    # Reservoir for water
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[p20_tiprack])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[p300_tiprack])

    # Define liquids
    water = protocol.define_liquid(name="water", description="Water for diluent", display_color="#0000FF")
    # Define sample liquids and load them into source plate wells
    sample_liquids = []
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#FF0000")
        sample_liquids.append(liq)
    # Load sample liquids into source plate wells (first 24 wells) with 100 ul each
    source_wells = list(source_plate.wells())[:24]
    for i, well in enumerate(source_wells):
        well.load_liquid(liquid=sample_liquids[i], volume=100)

    # Load water into reservoir well A1 with 2000 ul
    water_reservoir["A1"].load_liquid(liquid=water, volume=2000)

    # Volumes to transfer for each sample (sample_ul, diluent_ul)
    # Values from normalisation calculation
    sample_volumes = [
        {"sample_ul": 5.88, "diluent_ul": 44.12},
        {"sample_ul": 4.17, "diluent_ul": 45.83},
        {"sample_ul": 11.36, "diluent_ul": 38.64},
        {"sample_ul": 7.46, "diluent_ul": 42.54},
        {"sample_ul": 2.38, "diluent_ul": 47.62},
        {"sample_ul": 5.26, "diluent_ul": 44.74},
        {"sample_ul": 15.15, "diluent_ul": 34.85},
        {"sample_ul": 3.33, "diluent_ul": 46.67},
        {"sample_ul": 6.41, "diluent_ul": 43.59},
        {"sample_ul": 8.33, "diluent_ul": 41.67},
        {"sample_ul": 4.95, "diluent_ul": 45.05},
        {"sample_ul": 9.09, "diluent_ul": 40.91},
        {"sample_ul": 2.63, "diluent_ul": 47.37},
        {"sample_ul": 6.94, "diluent_ul": 43.06},
        {"sample_ul": 10.42, "diluent_ul": 39.58},
        {"sample_ul": 3.85, "diluent_ul": 46.15},
        {"sample_ul": 5.68, "diluent_ul": 44.32},
        {"sample_ul": 20.00, "diluent_ul": 30.00},
        {"sample_ul": 7.81, "diluent_ul": 42.19},
        {"sample_ul": 4.55, "diluent_ul": 45.45},
        {"sample_ul": 12.82, "diluent_ul": 37.18},
        {"sample_ul": 2.86, "diluent_ul": 47.14},
        {"sample_ul": 5.43, "diluent_ul": 44.57},
        {"sample_ul": 8.62, "diluent_ul": 41.38},
    ]

    # Transfer diluent then sample for each of the 24 samples
    for i in range(24):
        # Get volumes
        sample_vol = sample_volumes[i]["sample_ul"]
        diluent_vol = sample_volumes[i]["diluent_ul"]

        # Destination well
        dest_well = dest_plate.wells()[i]

        # Transfer diluent with p300
        p300.pick_up_tip()
        p300.aspirate(diluent_vol, water_reservoir["A1"])
        p300.dispense(diluent_vol, dest_well)
        p300.drop_tip()

        # Transfer sample with p20
        p20.pick_up_tip()
        source_well = source_plate.wells()[i]
        p20.aspirate(sample_vol, source_well)
        p20.dispense(sample_vol, dest_well)
        p20.mix(10, location=dest_well.display_name)  # mix after sample addition
        p20.drop_tip()

    # Protocol complete
    return
