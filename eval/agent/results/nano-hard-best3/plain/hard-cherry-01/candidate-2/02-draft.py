from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick and add master mix",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    master_mix_tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    # Define source liquids
    source_well_names = [
        "A1", "B2", "C3", "D4", "E5", "F6", "G7", "H8",
        "I9", "J10", "K11", "L12", "M13", "N14", "O15", "P16",
        "A17", "B18", "C19", "D20", "E21", "F22", "G23", "H24"
    ]
    for i, well in enumerate(source_well_names):
        liquid_obj = protocol.define_liquid(name=f"source_{well}", description=f"Source from {well}", display_color="#FF0000")
        source_plate[well].load_liquid(liquid=liquid_obj, volume=100)

    # Define mix
    mix_obj = protocol.define_liquid(name="mix", description="PCR master mix", display_color="#00FF00")
    master_mix_tube_rack["A1"].load_liquid(liquid=mix_obj, volume=500)

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
    for dest in ["A1","B1","C1","D1","E1","F1","G1","H1","A2","B2","C2","D2","E2","F2","G2","H2","A3","B3","C3","D3","E3","F3","G3","H3"]:
        src = dest_to_source[dest]
        # Transfer 2 ul sample
        p20.pick_up_tip()
        p20.aspirate(2, source_plate[src])
        p20.dispense(2, plate[dest])
        p20.drop_tip()
        # Transfer 18 ul mix
        p20.pick_up_tip()
        p20.aspirate(18, master_mix_tube_rack["A1"])
        p20.dispense(18, plate[dest])
        p20.drop_tip()
