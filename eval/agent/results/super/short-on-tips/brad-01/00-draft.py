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
    for i in range(1, 9):
        protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#00FF00")
    for i in range(1, 21):
        protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#0000FF")

    # Load liquids into wells
    # Bradford reagent in reservoir
    reservoir["A1"].load_liquid(liquid=bradford, volume=15000)  # 15 ml

    # Standards in plate (columns 6, rows A-H) each 50 ul
    std_wells = ["A6", "B6", "C6", "D6", "E6", "F6", "G6", "H6"]
    for idx, well in enumerate(std_wells, start=1):
        plate[well].load_liquid(liquid=protocol.define_liquid(name=f"standard {idx}", description="", display_color="#00FF00"), volume=50)

    # Samples in tuberack (assuming samples 1-20 in A1-T1? Actually 24 tube rack)
    # We'll place samples in column A rows 1-20? but rack only 2 rows? Use A1-P1 etc. Simpler: use first 20 positions A1..T1? but rack is 2 rows A-H, columns 1-12. Let's use column 1 rows A-H (8) and column2 rows A-H (8) and column3 rows A-D (4) =20.
    sample_positions = []
    for col in [1,2,3]:
        for row in ['A','B','C','D','E','F','G','H']:
            if len(sample_positions) >= 20:
                break
            sample_positions.append(f"{row}{col}")
        if len(sample_positions) >= 20:
            break
    for idx, pos in enumerate(sample_positions, start=1):
        tuberack[pos].load_liquid(liquid=protocol.define_liquid(name=f"sample {idx}", description="", display_color="#0000FF"), volume=500)

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
    std_wells_plate = column_down_wells(8)[40:48]  # next 8 wells

    # Transfer samples (duplicate)
    for i in range(0, 20, 1):
        src = tuberack[sample_positions[i]]
        # two destinations
        dest1 = plate[sample_wells[2*i]]
        dest2 = plate[sample_wells[2*i+1]]
        p20.pick_up_tip()
        p20.aspirate(5, src)
        p20.dispense(5, dest1)
        p20.dispense(5, dest2)
        p20.drop_tip()

    # Add Bradford reagent to all used wells (sample + standards)
    used_wells = sample_wells + std_wells_plate
    p300.pick_up_tip()
    p300.aspirate(250, reservoir["A1"])
    for well in used_wells:
        p300.dispense(250, plate[well])
        # optional mix
        p300.mix(2, 200, plate[well])
    p300.drop_tip()
