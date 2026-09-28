from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford_assay_20samples_duplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids and keep references
    liquids = {}
    liquids["bradford"] = protocol.define_liquid(
        name="bradford",
        description="Bradford reagent",
        display_color="#FF0000"
    )
    for i in range(1, 9):
        liquids[f"standard {i}"] = protocol.define_liquid(
            name=f"standard {i}",
            description=f"BSA standard {i}",
            display_color="#00FF00"
        )
    for i in range(1, 21):
        liquids[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color="#0000FF"
        )

    # Load labware
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    reservoir = protocol.load_labware("nest_1_reservoir_195ml", 4)

    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])

    # Load liquids into source wells
    # Load Bradford reagent
    reservoir["A1"].load_liquid(liquid=liquids["bradford"], volume=15000)

    # Load standards into plate wells A1-A8
    for i in range(1, 9):
        plate[f"A{i}"].load_liquid(liquid=liquids[f"standard {i}"], volume=100)

    # Load samples into tubes
    tube_map = {
        1: "A1", 2: "A2", 3: "A3", 4: "A4", 5: "A5", 6: "A6",
        7: "B1", 8: "B2", 9: "B3", 10: "B4", 11: "B5", 12: "B6",
        13: "C1", 14: "C2", 15: "C3", 16: "C4", 17: "C5", 18: "C6",
        19: "D1", 20: "D2"
    }
    for i in range(1, 21):
        tube_name = tube_map[i]
        tubes[tube_name].load_liquid(liquid=liquids[f"sample {i}"], volume=1500)

    # Helper to convert well index to well name
    def well_name(idx):
        row = (idx - 1) // 12
        col = (idx - 1) % 12 + 1
        return f"{chr(ord('A') + row)}{col}"

    # Transfer 5 ul of each sample into duplicate wells
    for i in range(1, 21):
        dest_idx_1 = 8 + 2*i - 1
        dest_idx_2 = 8 + 2*i
        dest_well_1 = well_name(dest_idx_1)
        dest_well_2 = well_name(dest_idx_2)
        src_tube = tube_map[i]

        # First well
        p300.pick_up_tip()
        p300.aspirate(5, tubes[src_tube])
        p300.dispense(5, plate[dest_well_1])
        p300.drop_tip()

        # Second well
        p300.pick_up_tip()
        p300.aspirate(5, tubes[src_tube])
        p300.dispense(5, plate[dest_well_2])
        p300.drop_tip()

    # Add 250 ul Bradford to each used well (standards + samples)
    for idx in range(1, 49):
        well = plate[well_name(idx)]
        p300.pick_up_tip()
        p300.aspirate(250, reservoir["A1"])
        p300.dispense(250, well)
        p300.drop_tip()
