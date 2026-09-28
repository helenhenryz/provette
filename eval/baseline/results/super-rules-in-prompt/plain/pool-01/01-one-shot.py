from opentrons import protocol_api

metadata = {
    "protocolName": "Pooled Library preparation",
    "author": "Assistant",
    "apiLevel": "2.19",
}

def run(protocol: protocol_api.ProtocolContext):
    # -------- Labware ----------
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)

    lib_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2
    )  # library plate

    tube_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 3
    )  # destination tube rack
    dest_tube = tube_rack["A1"]

    # -------- Pipette ----------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    p20.flow_rate.aspirate = 20
    p20.flow_rate.dispense = 20

    # -------- Liquids ----------
    lib_defs = {}
    for i in range(1, 49):
        name = f"library {i}"
        lib_defs[i] = protocol.define_liquid(
            name=name,
            description=f"Indexed sequencing library #{i}",
            display_color="#ffcc00",
        )
    # Load each library well with a realistic starting volume (20 µL)
    for i in range(1, 49):
        row_idx = (i - 1) % 8                # 0‑7 -> A-H
        col_num = (i - 1) // 8 + 1           # 0‑5 -> 1-6
        well_name = f"{chr(ord('A') + row_idx)}{col_num}"
        lib_plate[well_name].load_liquid(lib=lib_defs[i], volume=20)
    # Destination tube starts empty (no load_liquid call needed)

    # -------- Pooling ----------
    for i in range(1, 49):
        row_idx = (i - 1) % 8
        col_num = (i - 1) // 8 + 1
        src_well = lib_plate[f"{chr(ord('A') + row_idx)}{col_num}"]
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest_tube)
        p20.drop_tip()
