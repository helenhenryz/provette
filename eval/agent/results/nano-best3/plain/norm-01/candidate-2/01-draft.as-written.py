from opentrons import protocol_api

metadata = {
    "protocolName": "Normalization",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    protocol.define_liquid(name="water")
    for i in range(1, 25):
        protocol.define_liquid(name=f"sample {i}")

    # Load labware
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Load liquids into wells
    # Load water into reservoir well A1 with 1500 ul
    reservoir_well = reservoir["A1"]
    reservoir_well.load_liquid(liquid="water", volume=1500)

    # Load samples into source plate wells (100 ul each)
    for i in range(1, 25):
        if i <= 12:
            src_well_id = "A" + str(i)
        else:
            src_well_id = "B" + str(i-12)
        src_well = source_plate[src_well_id]
        src_well.load_liquid(liquid=f"sample {i}", volume=100)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Define sample and water volumes (from normalisation)
    sample_volumes = [5.88, 4.17, 11.36, 7.46, 2.38, 5.26, 15.15, 3.33, 6.41, 8.33, 4.95, 9.09, 2.63, 6.94, 10.42, 3.85, 5.68, 20.0, 7.81, 4.55, 12.82, 2.86, 5.43, 8.62]
    water_volumes = [44.12, 45.83, 38.64, 42.54, 47.62, 44.74, 34.85, 46.67, 43.59, 41.67, 45.05, 40.91, 47.37, 43.06, 39.58, 46.15, 44.32, 30.0, 42.19, 45.45, 37.18, 47.14, 44.57, 41.38]

    # Perform transfers
    for i in range(24):
        # Determine source well ID
        if i < 12:
            src_well_id = "A" + str(i+1)
        else:
            src_well_id = "B" + str(i+1-12)
        src_well = source_plate[src_well_id]

        # Destination well
        dest_well_id = dest_plate.wells()[i].name
        dest_well = dest_plate[dest_well_id]

        # Transfer sample with p20
        p20.pick_up_tip()
        p20.aspirate(sample_volumes[i], src_well)
        p20.dispense(sample_volumes[i], dest_well)
        p20.drop_tip()

        # Transfer water with p300
        p300.pick_up_tip()
        p300.aspirate(water_volumes[i], reservoir["A1"])
        p300.dispense(water_volumes[i], dest_well)
        p300.drop_tip()
