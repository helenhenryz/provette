from opentrons import protocol_api

metadata = {"protocolName": "Bradford assay for 20 protein samples in duplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Define liquids
    protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#0000FF")
    for i in range(1, 9):
        protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#FF0000")
    for i in range(1, 21):
        protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#00FF00")

    # Load liquids onto the deck
    # Load standards into plate wells A1-A8
    for i in range(1, 9):
        plate[f"A{i}"].load_liquid(liquid=f"standard {i}", volume=10)

    # Map sample tubes: A1-A12, B1-B12 (first 20 positions)
    sample_tube_wells = []
    for row in range(1, 13):
        sample_tube_wells.append(f"A{row}")
    for row in range(1, 13):
        sample_tube_wells.append(f"B{row}")
    # Load samples into tube rack
    for i in range(1, 21):
        src_well = sample_tube_wells[i-1]
        tubes[src_well].load_liquid(liquid=f"sample {i}", volume=1000)

    # Load Bradford reagent into reservoir
    reservoir["A1"].load_liquid(liquid="bradford", volume=15000)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])

    # Generate list of all wells in column-major order
    all_wells = []
    for col in ["A","B","C","D","E","F","G","H"]:
        for row in range(1, 13):
            all_wells.append(col+row)

    # Determine sample target wells (skip first 8 standard wells)
    sample_target_wells = all_wells[8:48]  # 40 wells
    used_wells = [f"A{i}" for i in range(1, 9)] + sample_target_wells

    # Iterate over samples and dispense 5 ul into two wells each
    sample_target_iter = iter(sample_target_wells)
    for i in range(1, 21):
        well1 = next(sample_target_iter)
        well2 = next(sample_target_iter)
        src_well = sample_tube_wells[i-1]  # map sample i to tube rack well
        # First replicate
        p20.pick_up_tip()
        p20.aspirate(5, tubes[src_well])
        p20.dispense(5, plate[well1])
        p20.drop_tip()
        # Second replicate
        p20.pick_up_tip()
        p20.aspirate(5, tubes[src_well])
        p20.dispense(5, plate[well2])
        p20.drop_tip()

    # Add 250 ul Bradford reagent to all used wells
    p300.pick_up_tip()
    p300.aspirate(250, reservoir["A1"])
    for well in used_wells:
        p300.dispense(250, plate[well])
    p300.drop_tip()
