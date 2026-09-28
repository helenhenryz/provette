from opentrons import protocol_api

metadata = {"protocolName": "MIC_Plate_2_Antibiotics", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids
    antibiotic_1 = protocol.define_liquid(name="antibiotic 1", description="stock antibiotic 1", display_color="#FF0000")
    antibiotic_2 = protocol.define_liquid(name="antibiotic 2", description="stock antibiotic 2", display_color="#00FF00")
    broth = protocol.define_liquid(name="broth", description="Mueller-Hinton broth", display_color="#0000FF")
    culture = protocol.define_liquid(name="culture", description="bacterial culture", display_color="#FFFF00")

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=antibiotic_1, volume=200)
    tubes["A2"].load_liquid(liquid=antibiotic_2, volume=200)
    reservoir["A1"].load_liquid(liquid=broth, volume=2000)
    tubes["A3"].load_liquid(liquid=culture, volume=2000)

    # Dilution series for antibiotic 1 (row A)
    for col in range(1, 11):
        target = plate[f"A{col}"]
        p300.pick_up_tip()
        # Add 50 ul broth
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, target)
        # Transfer 50 ul from source
        if col == 1:
            source = tubes["A1"]
        else:
            source = plate[f"A{col-1}"]
        p300.aspirate(50, source)
        p300.dispense(50, target)
        # Mix
        p300.mix(3, 30, target)
        # Remove 50 ul to waste from the last well
        if col == 10:
            p300.aspirate(50, target)
            p300.dispense(50, reservoir["A2"])  # waste
        p300.drop_tip()

    # Dilution series for antibiotic 2 (row B)
    for col in range(1, 11):
        target = plate[f"B{col}"]
        p300.pick_up_tip()
        # Add 50 ul broth
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, target)
        # Transfer 50 ul from source
        if col == 1:
            source = tubes["A2"]
        else:
            source = plate[f"B{col-1}"]
        p300.aspirate(50, source)
        p300.dispense(50, target)
        # Mix
        p300.mix(3, 30, target)
        # Remove 50 ul to waste from the last well
        if col == 10:
            p300.aspirate(50, target)
            p300.dispense(50, reservoir["A2"])  # waste
        p300.drop_tip()

    # Add 50 ul culture to each well in columns 1-11
    for col in range(1, 12):
        for row in ["A", "B"]:
            well = plate[f"{row}{col}"]
            p300.pick_up_tip()
            p300.aspirate(50, tubes["A3"])
            p300.dispense(50, well)
            p300.drop_tip()

    # Add 50 ul broth to column 11 wells (growth control)
    for row in ["A", "B"]:
        well = plate[f"{row}11"]
        p300.pick_up_tip()
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, well)
        p300.drop_tip()

    # Add 100 ul broth to column 12 (sterility control)
    for row in ["A", "B"]:
        well = plate[f"{row}12"]
        p300.pick_up_tip()
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, well)
        p300.drop_tip()
