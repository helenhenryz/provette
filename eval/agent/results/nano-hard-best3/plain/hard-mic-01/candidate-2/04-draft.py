from opentrons import protocol_api

metadata = {"protocolName": "MIC plate for 2 antibiotics", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    broth_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

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

    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Serial dilution for antibiotic 1 (row A)
    p300.pick_up_tip()
    for i in range(1, 11):
        # Add 50 ul of broth to well A{i}
        p300.aspirate(50, broth_reservoir["A1"])
        p300.dispense(50, plate[f"A{i}"])
        # Transfer 50 ul of antibiotic 1 (stock for i==1, previous well for i>1)
        if i == 1:
            p300.aspirate(50, tubes["A1"])
        else:
            p300.aspirate(50, plate[f"A{i-1}"])
        p300.dispense(50, plate[f"A{i}"])
        # Mix
        p300.mix(10, 5, plate[f"A{i}"])
        # Remove 50 ul from the last well to waste
        if i == 10:
            p300.aspirate(50, plate[f"A{i}"])
    p300.drop_tip()

    # Serial dilution for antibiotic 2 (row B)
    p300.pick_up_tip()
    for i in range(1, 11):
        # Add 50 ul of broth to well B{i}
        p300.aspirate(50, broth_reservoir["A1"])
        p300.dispense(50, plate[f"B{i}"])
        # Transfer 50 ul of antibiotic 2 (stock for i==1, previous well for i>1)
        if i == 1:
            p300.aspirate(50, tubes["A2"])
        else:
            p300.aspirate(50, plate[f"B{i-1}"])
        p300.dispense(50, plate[f"B{i}"])
        # Mix
        p300.mix(10, 5, plate[f"B{i}"])
        # Remove 50 ul from the last well to waste
        if i == 10:
            p300.aspirate(50, plate[f"B{i}"])
    p300.drop_tip()

    # Add 50 ul of culture to wells A1-A11 and B1-B11
    culture_wells = [f"A{i}" for i in range(1, 12)] + [f"B{i}" for i in range(1, 12)]
    while culture_wells:
        n_wells = min(6, len(culture_wells))
        # Aspirate 50 ul * n_wells of culture
        p300.pick_up_tip()
        p300.aspirate(50 * n_wells, tubes["A3"])
        # Dispense 50 ul into each well
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
