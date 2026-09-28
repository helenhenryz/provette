metadata = {
    "protocolName": "Cherrypick 10ul samples",
    "author": "",
    "description": "Transfer 10ul from specified source wells to consecutive destination wells starting at A1.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------
    # Labware
    # ------------------------------------------------------------------
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

    # ------------------------------------------------------------------
    # Liquids (define each distinct liquid present at start)
    # ------------------------------------------------------------------
    # Every source well contains a unique sample; we represent them here as individual liquids.
    # Names follow the requested format (<source‑well>_sample).
    samples = {}
    for coord in ["B3","C7","D1","A12","H6","E5","F9","G2","B11","C4"]:
        liq_name = f"{coord}_sample"
        liquid = protocol.define_liquid(name=liq_name,
                                        description=f"Sample originally in {coord}",
                                        display_color="#FF0000")
        source_plate[coord].load_liquid(liquid=liquid, volume=100)  # start with ample volume
        samples[coord] = liquid

    destination_liquid = None  # destinations start empty; no liquid definition needed.

    # ------------------------------------------------------------------
    # Pipette
    # ------------------------------------------------------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # ------------------------------------------------------------------
    # Transfer steps
    # ------------------------------------------------------------------
    source_coords = ["B3","C7","D1","A12","H6","E5","F9","G2","B11","C4"]
    # Generate consecutive destination coordinates starting at A1 and proceeding
    # across rows (A1, A2, … A12, B1, B2, …).
    dest_coords = []
    idx = 0
    while len(dest_coords) < len(source_coords):
        row_idx = idx // 12               # which 0‑based row
        col_idx = (idx % 12) + 1          # 1‑based column
        row_letter = chr(ord('A') + row_idx)
        dest_coords.append(f"{row_letter}{col_idx}")
        idx += 1

    # Perform transfers, using a fresh tip for each to avoid cross‑contamination.
    for src, dst in zip(source_coords, dest_coords):
        p20.pick_up_tip()
        p20.aspirate(10, source_plate[src].bottom(z=0.5))  # safely aspirate near bottom
        p20.dispense(10, dest_plate[dst].top(z=-0.5))      # dispense just above well surface
        p20.drop_tip()

# End of protocol
