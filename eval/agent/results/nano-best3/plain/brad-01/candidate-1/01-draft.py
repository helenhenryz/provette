from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    bradford_liquid = protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000")
    for i in range(1, 9):
        protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#808080")
    for i in range(1, 21):
        protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#00FF00")

    # Load labware
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Load standards into plate wells A1-A8
    for i in range(1, 9):
        well = plate[f"A{i}"]
        std_liquid = protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#808080")
        well.load_liquid(liquid=std_liquid, volume=5)

    # Load samples into tuberack wells
    tube_well_names = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6","C1","C2","C3","C4","C5","D1","D2","D3","D4","D5","D6"]
    for i in range(1, 21):
        src_well = tuberack[tube_well_names[i-1]]
        sample_liquid = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#00FF00")
        src_well.load_liquid(liquid=sample_liquid, volume=1000)

    # Load Bradford into reservoir well A1
    bradford_reservoir_well = reservoir["A1"]
    bradford_reservoir_well.load_liquid(liquid=bradford_liquid, volume=15000)

    # Helper function to convert well index to name
    def index_to_well(idx):
        zero_idx = idx - 1
        row = zero_idx // 12
        col = zero_idx % 12
        return f"{chr(65+row)}{col+1}"

    # Define standard wells (A1-A8)
    standard_well_names = [f"A{i}" for i in range(1,9)]

    # Define sample destination wells (indices 9-48)
    sample_dest_well_names = []
    for i in range(1, 21):
        idx1 = 8 + 2*i - 1
        idx2 = 8 + 2*i
        sample_dest_well_names.append(index_to_well(idx1))
        sample_dest_well_names.append(index_to_well(idx2))

    # Perform transfers for each sample
    for i in range(1, 21):
        src_well = tuberack[tube_well_names[i-1]]
        dest_well_1 = plate[sample_dest_well_names[2*(i-1)]]
        dest_well_2 = plate[sample_dest_well_names[2*(i-1)+1]]
        for dest_well in [dest_well_1, dest_well_2]:
            p300.pick_up_tip()
            p300.aspirate(5, src_well)
            p300.dispense(5, dest_well)
            p300.aspirate(250, bradford_reservoir_well)
            p300.dispense(250, dest_well)
            p300.drop_tip()

    # Add Bradford to standard wells
    for std_well_name in standard_well_names:
        std_well = plate[std_well_name]
        p300.pick_up_tip()
        p300.aspirate(250, bradford_reservoir_well)
        p300.dispense(250, std_well)
        p300.drop_tip()
