from opentrons import protocol_api

metadata = {"protocolName": "MIC plate for 2 antibiotics", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    broth_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 6)

    # Define liquids
    antibiotic_1 = protocol.define_liquid(name="antibiotic 1", description="Antibiotic 1 stock", display_color="#FF0000")
    antibiotic_2 = protocol.define_liquid(name="antibiotic 2", description="Antibiotic 2 stock", display_color="#00FF00")
    broth = protocol.define_liquid(name="broth", description="Mueller-Hinton broth", display_color="#0000FF")
    culture = protocol.define_liquid(name="culture", description="Bacterial culture", display_color="#FFA500")

    # Load liquids into source wells
    broth_reservoir["A1"].load_liquid(liquid=broth, volume=2000)
    tubes["A1"].load_liquid(liquid=antibiotic_1, volume=1000)
    tubes["A2"].load_liquid(liquid=antibiotic_2, volume=1000)
    tubes["A3"].load_liquid(liquid=culture, volume=2000)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Volumes for antibiotic 1 (row A)
    row_A = [
        ("A1", 25, 25),
        ("A2", 12.5, 37.5),
        ("A3", 6.25, 43.75),
        ("A4", 3.125, 46.875),
        ("A5", 1.5625, 48.4375),
        ("A6", 0.78125, 49.21875),
        ("A7", 0.390625, 49.609375),
        ("A8", 0.1953125, 49.8046875),
        ("A9", 0.09765625, 49.90234375),
        ("A10", 0.048828125, 49.951171875),
        ("A11", 0, 50)
    ]
    # Add antibiotic 1 to wells
    for well, antib_vol, broth_vol in row_A:
        p20.pick_up_tip()
        p20.aspirate(antib_vol, tubes["A1"])
        p20.dispense(antib_vol, plate[well])
        p20.drop_tip()

    # Add broth to row A wells
    for well, antib_vol, broth_vol in row_A:
        p300.pick_up_tip()
        p300.aspirate(broth_vol, broth_reservoir["A1"])
        p300.dispense(broth_vol, plate[well])
        p300.mix(10, 40, plate[well])
        p300.drop_tip()

    # Volumes for antibiotic 2 (row B)
    row_B = [
        ("B1", 25, 25),
        ("B2", 12.5, 37.5),
        ("B3", 6.25, 43.75),
        ("B4", 3.125, 46.875),
        ("B5", 1.5625, 48.4375),
        ("B6", 0.78125, 49.21875),
        ("B7", 0.390625, 49.609375),
        ("B8", 0.1953125, 49.8046875),
        ("B9", 0.09765625, 49.90234375),
        ("B10", 0.048828125, 49.951171875),
        ("B11", 0, 50)
    ]
    # Add antibiotic 2 to wells
    for well, antib_vol, broth_vol in row_B:
        p20.pick_up_tip()
        p20.aspirate(antib_vol, tubes["A2"])
        p20.dispense(antib_vol, plate[well])
        p20.drop_tip()

    # Add broth to row B wells
    for well, antib_vol, broth_vol in row_B:
        p300.pick_up_tip()
        p300.aspirate(broth_vol, broth_reservoir["A1"])
        p300.dispense(broth_vol, plate[well])
        p300.mix(10, 40, plate[well])
        p300.drop_tip()

    # Add 50 ul of culture to wells A1-A11 and B1-B11
    culture_wells = [well for well, _, _ in row_A] + [well for well, _, _ in row_B]
    while culture_wells:
        n_wells = min(6, len(culture_wells))
        p300.pick_up_tip()
        p300.aspirate(50 * n_wells, tubes["A3"])
        for j in range(n_wells):
            well = culture_wells.pop(0)
            p300.dispense(50, plate[well])
        p300.drop_tip()

    # Add 100 ul of broth to wells A12 and B12 (sterility control)
    p300.pick_up_tip()
    p300.aspirate(200, broth_reservoir["A1"])
    p300.dispense(100, plate["A12"])
    p300.dispense(100, plate["B12"])
    p300.drop_tip()
