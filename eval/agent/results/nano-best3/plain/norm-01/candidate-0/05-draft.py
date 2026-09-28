from opentrons import protocol_api

metadata = {
    "protocolName": "Normalization",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip_rack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Load instruments
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack_300])

    # Define liquids
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    samples = {}
    for i in range(1, 25):
        samples[i] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color=f"#{i:06X}")

    # Load water into reservoir
    reservoir_well = reservoir["A1"]
    reservoir_well.load_liquid(liquid=water, volume=5000)

    # Volumes from normalisation (ul)
    sample_volumes = {
        1: 5.88, 2: 4.17, 3: 11.36, 4: 7.46, 5: 2.38, 6: 5.26, 7: 15.15, 8: 3.33,
        9: 6.41, 10: 8.33, 11: 4.95, 12: 9.09, 13: 2.63, 14: 6.94, 15: 10.42, 16: 3.85,
        17: 5.68, 18: 20.0, 19: 7.81, 20: 4.55, 21: 12.82, 22: 2.86, 23: 5.43, 24: 8.62
    }
    diluent_volumes = {
        1: 44.12, 2: 45.83, 3: 38.64, 4: 42.54, 5: 47.62, 6: 44.74, 7: 34.85, 8: 46.67,
        9: 43.59, 10: 41.67, 11: 45.05, 12: 40.91, 13: 47.37, 14: 43.06, 15: 39.58, 16: 46.15,
        17: 44.32, 18: 30.0, 19: 42.19, 20: 45.45, 21: 37.18, 22: 47.14, 23: 44.57, 24: 41.38
    }

    # Generate the well‑name order required by the plate map
    expected_well_names = []
    for row in range(1, 9):                     # rows 1‑8
        for col_idx in range(8):                # columns H‑>A
            col_letter = chr(ord('H') - col_idx)  # H, G, F, …, A
            well_name = f"{col_letter}{row}"
            expected_well_names.append(well_name)
            if len(expected_well_names) == 24:
                break
        if len(expected_well_names) == 24:
            break

    # Load each sample into its destination well
    for i in range(1, 25):
        well_name = expected_well_names[i-1]
        dest_well = dest_plate[well_name]
        dest_well.load_liquid(liquid=samples[i], volume=sample_volumes[i])

    # Transfer water to each well
    for i in range(1, 25):
        well_name = expected_well_names[i-1]
        vol_diluent = diluent_volumes[i]
        dest_well = dest_plate[well_name]
        p300.pick_up_tip()
        p300.aspirate(vol_diluent, reservoir["A1"])
        p300.dispense(vol_diluent, dest_well)
        p300.drop_tip()
