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
    # Bradford reagent
    bradford_liquid = protocol.define_liquid(
        name="bradford",
        description="Bradford reagent",
        display_color="#FF0000"
    )
    # BSA standards 1-8
    standard_liquids = {}
    for i in range(1, 9):
        standard_liquids[f"standard {i}"] = protocol.define_liquid(
            name=f"standard {i}",
            description=f"BSA standard {i}",
            display_color="#000000"
        )
    # Samples 1-20
    sample_liquids = {}
    for i in range(1, 21):
        sample_liquids[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color="#0000FF"
        )

    # Load standards (100 µL each) into wells A1-A8
    standard_wells = ["A1","A2","A3","A4","A5","A6","A7","A8"]
    for i, well_name in enumerate(standard_wells, start=1):
        plate[well_name].load_liquid(
            liquid=standard_liquids[f"standard {i}"],
            volume=100
        )

    # Load Bradford reagent (15000 µL) into reservoir well A1
    bradford_reservoir["A1"].load_liquid(
        liquid=bradford_liquid,
        volume=15000
    )

    # Define the mapping of source wells to destination wells
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

    # Load each sample (10 µL) into its source well in the tube rack
    for idx, info in enumerate(sample_mapping, start=1):
        src_well = info["source"]
        sample_liquid_obj = sample_liquids[f"sample {idx}"]
        tuberack[src_well].load_liquid(
            liquid=sample_liquid_obj,
            volume=10
        )

    # Transfer samples in duplicate (2x5 µL) using p20_multi
    # One fresh tip per sample to avoid cross‑contamination
    for info in sample_mapping:
        p20_multi.pick_up_tip(tip_racks=[tip_racks_20])
        # First transfer: aspirate 5 µL from source, dispense to dest1
        p20_multi.aspirate(5, tuberack[info["source"]])
        p20_multi.dispense(5, plate[info["dest1"]])
        # Second transfer: aspirate 5 µL from same source again, dispense to dest2
        p20_multi.aspirate(5, tuberack[info["source"]])
        p20_multi.dispense(5, plate[info["dest2"]])
        p20_multi.drop_tip()

    # Collect all wells that need Bradford reagent (standards + sample destinations)
    standard_and_sample_wells = standard_wells.copy()
    for info in sample_mapping:
        standard_and_sample_wells.append(info["dest1"])
        standard_and_sample_wells.append(info["dest2"])

    # Add 250 µL of Bradford reagent to each well
    p300_multi.pick_up_tip(tip_racks=[tip_racks_300])
    for well in standard_and_sample_wells:
        p300_multi.aspirate(250, bradford_reservoir["A1"])
        p300_multi.dispense(250, plate[well])
    p300_multi.drop_tip()
