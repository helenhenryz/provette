from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypicking Protocol",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tube_rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define source liquids (one per source well)
    source_wells = ["A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8", "I9", "J10", "K11", "L12", "M13", "N14", "O15", "P16", "A17", "B18", "C19", "D20", "E21", "F22", "G23", "H24"]
    for well in source_wells:
        liquid_name = f"source_{well}"
        protocol.define_liquid(name=liquid_name, description=None, display_color='#1f77b4')
        source_plate[well].load_liquid(liquid=liquid_name, volume=100)

    # Define mix (PCR master mix)
    protocol.define_liquid(name="mix", description="PCR master mix", display_color="#FF0000")
    tube_rack["A1"].load_liquid(liquid="mix", volume=500)

    # Mapping from destination well to source well
    dest_to_source = {
        "A1": "A1",
        "B1": "B2",
        "C1": "C3",
        "D1": "D4",
        "E1": "E5",
        "F1": "F6",
        "G1": "G7",
        "H1": "H8",
        "A2": "I9",
        "B2": "J10",
        "C2": "K11",
        "D2": "L12",
        "E2": "M13",
        "F2": "N14",
        "G2": "O15",
        "H2": "P16",
        "A3": "A17",
        "B3": "B18",
        "C3": "C19",
        "D3": "D20",
        "E3": "E21",
        "F3": "F22",
        "G3": "G23",
        "H3": "H24"
    }

    # Perform transfers
    for dest_well, source_well in dest_to_source.items():
        p20.pick_up_tip()
        # aspirate 2 ul from source well
        p20.aspirate(2, source_plate[source_well])
        # aspirate 18 ul from mix tube
        p20.aspirate(18, tube_rack["A1"])
        # dispense total 20 ul into destination well
        p20.dispense(20, dest_plate[dest_well])
        p20.drop_tip()
