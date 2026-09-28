import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Bradford assay 20 samples duplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 3)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 5)

    # Define liquids
    bradford = protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FFA500")
    std_liquids = {}
    for i in range(1, 9):
        liq = protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#00FF00")
        std_liquids[f"standard {i}"] = liq
    sample_liquids = {}
    for i in range(1, 21):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#0000FF")
        sample_liquids[f"sample {i}"] = liq

    # Load liquids into wells
    reservoir["A1"].load_liquid(liquid=bradford, volume=15000)  # 15 ml

    # Standards in plate (columns 6, rows A-H) each 50 ul
    std_wells = ["A6", "B6", "C6", "D6", "E6", "F6", "G6", "H6"]
    for idx, well in enumerate(std_wells, start=1):
        plate[well].load_liquid(liquid=std_liquids[f"standard {idx}"], volume=50)

    # Samples in tuberack: use first 20 wells in column-down order (A1-D6)
    sample_positions = []
    for col in range(1, 7):  # columns 1-6
        for row in ['A','B','C','D']:
            if len(sample_positions) >= 20:
                break
            sample_positions.append(f"{row}{col}")
        if len(sample_positions) >= 20:
            break
    for idx, pos in enumerate(sample_positions, start=1):
        tuberack[pos].load_liquid(liquid=sample_liquids[f"sample {idx}"], volume=500)

    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    # Helper to get well list in column-down order
    def column_down_wells(n):
        wells = []
        for col in range(1, 13):
            for row in ['A','B','C','D','E','F','G','H']:
                wells.append(f"{row}{col}")
                if len(wells) == n:
                    return wells
        return wells

    sample_wells = column_down_wells(40)  # first 40 wells for samples
    all_wells = column_down_wells(48)
    std_wells_plate = all_wells[40:48]

    # Step 1: Add Bradford reagent to all wells that will be used (samples + standards)
    used_wells = sample_wells + std_wells_plate
    p300.pick_up_tip()
    for well in used_wells:
        p300.aspirate(250, reservoir["A1"])
        p300.dispense(250, plate[well])
        # Mix: 5 cycles of 200 ul (≈80% of 250 ul)
        p300.mix(5, 200, plate[well])
    p300.drop_tip()

    # Step 2: Add samples (5 ul) in duplicate
    for i in range(20):
        src = tuberack[sample_positions[i]]
        dest1 = plate[sample_wells[2*i]]
        dest2 = plate[sample_wells[2*i+1]]
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(5, dest1)
        p20.aspirate(5, src)
        p20.dispense(5, dest2)
        p20.drop_tip()

    # Optional brief mix after sample addition (not required)
    # p300.pick_up_tip()
    # for well in used_wells:
    #     p300.aspirate(150, reservoir["A1"])  # just to flush tip
    #     p300.dispense(150, reservoir["A1"])
    # p300.drop_tip()
