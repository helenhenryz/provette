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

    # Normalisation calculation
    norm = normalise(
        concentrations=[85,120,44,67,210,95,33,150,78,60,101,55,190,72,48,130,88,25,64,110,39,175,92,58],
        target=10,
        final_volume_ul=50
    )
    samples = norm["samples"]

    # Transfer diluent then sample for each of the 24 samples
    for i in range(24):
        # Get volumes
        sample_vol = samples[i]["sample_ul"]
        diluent_vol = samples[i]["diluent_ul"]

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
        p20.drop_tip()

    # Protocol complete
    return
