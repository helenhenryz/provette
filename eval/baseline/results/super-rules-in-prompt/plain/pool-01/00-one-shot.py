from opentrons import protocol_api

metadata = {
    "protocolName": "Pooled Library preparation",
    "author": "Assistant",
    "apiLevel": "2.19",
}

def run(protocol: protocol_api.ProtocolContext):
    # -------- Labware ----------
    # tip rack for p20
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)

    # plate containing the 48 libraries (columns 1‑6 fully populated)
    lib_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", 2, name="library plate"
    )

    # tube rack for the destination 1.5 ml tube
    tube_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 3, name="pooled tube rack"
    )

    # Destination tube (use first slot A1)
    dest_tube = tube_rack["A1"]

    # -------- Pipette ----------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    p20.flow_rate.aspirate = 20   # µL/s – reasonable for low viscosity
    p20.flow_rate.dispense   = 20

    # -------- Liquids ----------
    # Define each library liquid uniquely
    lib_defs = {}
    for i in range(1, 49):
        name = f"library {i}"
        lib_defs[i] = protocol.define_liquid(
            name=name,
            description=f"Indexed sequencing library #{i}",
            display_color="#ffcc00",  # amber, arbitrary but constant
        )

    # Pre-load each library well with a realistic starting volume (e.g., 20 µL)
    for i in range(1, 49):
        # map index to well coordinates: rows A‑H, columns 1‑6
        row_idx = (i - 1) % 8          # 0‑7 → A‑H
        col_num = (i - 1) // 8 + 1     # 0‑5 → 1‑6
        well_name = f"{chr(ord('A') + row_idx)}{col_num}"
        lib_plate[well_name].load_liquid(lib=lib_defs[i], volume=20)

    # Optional: indicate the tube starts empty (no liquid loaded)

    # -------- Pooling ----------
    p20.transfer(
        volume=5,
        source=[pl.well for pl in [
            lib_plate[f"{chr(ord('A') + ((i-1)%8))}{((i-1)//8+1)}"]
            for i in range(1, 49)
        ]],
        dest=[dest_tube]*48,
        new_tip='always',
    )
'''
Notes on correctness per the supplied rules:
- Every tip is picked up fresh (`new_tip='always'`), eliminating concerns of cross‑contamination or “stock” misuse.
- Aspiration volume (5 µl) ≥ p20 minimum (~1 µl) and ≤ maximum (20 µl).
- Dispensing adds a maximal total of 48 × 5 = 240 µl to the 1.5 ml tube – far below its capacity.
- No mixing steps performed; thus mixing rules are silent/no‑warning.
- Temperature modules, etc., are not used → associated rules do not apply.
'''
