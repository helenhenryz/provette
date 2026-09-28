from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks_20 = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    tip_racks_300 = protocol.load_labware("opentrons_96_tiprack_300ul", "2")
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "3")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "4")
    bradford_reservoir = protocol.load_labware("nest_1_reservoir_195ml", "5")

    # Load instruments
    p20_multi = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tip_racks_20])
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tip_racks_300])

    # Define liquids
    protocol.define_liquid(
        name="bradford",
        description="Bradford reagent",
        display_color="#FF0000"
    )
    for i in range(1, 9):
        protocol.define_liquid(
            name=f"standard {i}",
            description=f"BSA standard {i}",
            display_color="#000000"
        )
    for i in range(1, 21):
        protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color="#0000FF"
        )

    # Load liquids into plate and reservoir
    standard_wells = ["A1","A2","A3","A4","A5","A6","A7","A8"]
    for i, well_name in enumerate(standard_wells, start=1):
        plate[well_name].load_liquid(liquid=f"standard {i}", volume=100)

    bradford_reservoir["A1"].load_liquid(liquid="bradford", volume=15000)

    # Define sample mapping
    sample_mapping = [
        {"source": "A1", "dest1": "A9", "dest2": "A10"},
        {"source": "A2", "dest1": "A11", "dest2": "A12"},
        {"source": "A3", "dest1": "B1", "dest2": "B2"},
        {"source": "A4", "dest1": "B3", "dest2": "B4"},
        {"source": "A5", "dest1": "B5", "dest2": "B6"},
        {"source": "A6", "dest1": "B7", "dest2": "B8"},
        {"source": "B1", "dest1": "B9", "dest2": "B10"},
        {"source": "B2", "dest1": "B11", "dest2": "B12"},
        {"source": "B3", "dest1": "C1", "dest2": "C2"},
        {"source": "B4", "dest1": "C3", "dest2": "C4"},
        {"source": "B5", "dest1": "C5", "dest2": "C6"},
        {"source": "B6", "dest1": "C7", "dest2": "C8"},
        {"source": "C1", "dest1": "C9", "dest2": "C10"},
        {"source": "C2", "dest1": "C11", "dest2": "C12"},
        {"source": "C3", "dest1": "D1", "dest2": "D2"},
        {"source": "C4", "dest1": "D3", "dest2": "D4"},
        {"source": "C5", "dest1": "D5", "dest2": "D6"},
        {"source": "C6", "dest1": "D7", "dest2": "D8"},
        {"source": "D1", "dest1": "D9", "dest2": "D10"},
        {"source": "D2", "dest1": "D11", "dest2": "D12"},
    ]

    # Create replicate lists
    first_replicates = []
    second_replicates = []
    for info in sample_mapping:
        first_replicates.append((info["source"], info["dest1"]))
        second_replicates.append((info["source"], info["dest2"]))

    # Chunk function
    def chunk(lst, n):
        return [lst[i:i+n] for i in range(0, len(lst), n)]

    groups_first = chunk(first_replicates, 8)
    groups_second = chunk(second_replicates, 8)

    # Perform sample transfers with p20_multi
    for group in groups_first:
        p20_multi.pick_up_tip()
        src_wells = [src for src, dest in group]
        p20_multi.aspirate(5, [tuberack[src] for src in src_wells])
        for src, dest in group:
            p20_multi.dispense(5, plate[dest])
        p20_multi.drop_tip()

    for group in groups_second:
        p20_multi.pick_up_tip()
        src_wells = [src for src, dest in group]
        p20_multi.aspirate(5, [tuberack[src] for src in src_wells])
        for src, dest in group:
            p20_multi.dispense(5, plate[dest])
        p20_multi.drop_tip()

    # Add Bradford reagent to all used wells (samples + standards)
    sample_wells = [dest for _, dest in first_replicates] + [dest for _, dest in second_replicates]
    all_wells = standard_wells + sample_wells

    def chunk_wells(wells, n):
        return [wells[i:i+n] for i in range(0, len(wells), n)]

    groups_all = chunk_wells(all_wells, 8)

    # Use a single tip for all Bradford dispensing
    p300_multi.pick_up_tip()
    for group in groups_all:
        p300_multi.aspirate(250, bradford_reservoir["A1"])
        for well in group:
            p300_multi.dispense(250, plate[well])
    p300_multi.drop_tip()
