metadata = {
    "protocolName": "ELISA Sample and Standard Addition",
    "author": "",
    "apiLevel": "2.19"
}

from opentrons import protocol_api


def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware ------------------------------------------------------------
    # Source plate containing the 40 serum samples (columns 1‑5, rows A‑H)
    src_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", 1, "serum source plate"
    )
    # Tube rack holding the 8 standards (one tube per standard, column 1)
    std_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "standard tube rack"
    )
    # Destination ELISA plate (coated, ready for additions)
    dst_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", 3, "ELISA plate"
    )
    # Tip rack for single‑channel p300
    tiprack = protocol.load_labware(
        "opentrons_96_tiprack_300ul", 4, "tip rack"
    )

    # ---- Pipette ------------------------------------------------------------
    p300 = protocol.load_instrument(
        "p300_single_gen2", "right", tip_racks=[tiprack]
    )

    # ---- Liquid definitions -------------------------------------------------
    rows = ["A", "B", "C", "D", "E", "F", "G", "H"]
    # Colors – use a simple repeating pattern; any valid hex string is fine.
    base_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00",
                   "#FF00FF", "#00FFFF", "#FFFFFF", "#000000"]

    serums = {}          # name -> Liquid object
    standards = {}       # name -> Liquid object

    # Define serum liquids
    for i in range(1, 41):
        name = f"serum {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"Serum sample {i}",
            display_color=base_colors[(i - 1) % len(base_colors)]
        )
        serums[name] = liq

    # Define standard liquids
    for i in range(1, 9):
        name = f"standard {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"Standard {i}",
            display_color=base_colors[(i + 10) % len(base_colors)]  # offset to differ visually
        )
        standards[name] = liq

    # Load liquids onto labware ------------------------------------------------

    # Load sera into source plate (columns 1‑5)
    serum_idx = 0
    for col in range(1, 6):               # columns 1‑5 inclusive
        for row in rows:
            well_name = f"{row}{col}"
            src_well = src_plate[well_name]
            src_well.load_liquid(
                liquid=serums[f"serum {serum_idx + 1}"],
                volume=180                  # µL – fits in a 200 µL well
            )
            serum_idx += 1

    # Load standards into tube rack (column 1, rows A‑H)
    std_idx = 0
    for row in rows:
        tube_well = f"{row}1"
        std_well = std_rack[tube_well]
        std_well.load_liquid(
            liquid=standards[f"standard {std_idx + 1}"],
            volume=500                     # µL – ample for a 100 µL transfer
        )
        std_idx += 1

    # ---- Transfer serums ----------------------------------------------------
    serum_idx = 0
    for col in range(1, 6):
        for row in rows:
            src_well_name = f"{row}{col}"
            dst_well_name = f"{row}{col}"   # matching well on ELISA plate
            p300.pick_up_tip()
            p300.aspirate(100, src_plate[src_well_name])
            p300.dispense(100, dst_plate[dst_well_name])
            p300.blink()                    # optional visual cue, harmless
            p300.drop_tip()
            serum_idx += 1

    # ---- Transfer standards to column 12 ------------------------------------
    std_idx = 0
    for row in rows:
        tube_well = f"{row}1"
        dst_well_name = f"{row}12"
        p300.pick_up_tip()
        p300.aspirate(100, std_rack[tube_well])
        p300.dispense(100, dst_plate[dst_well_name])
        p300.blink()
        p300.drop_tip()
        std_idx += 1

if __name__ == "__main__":
    # Optional: allow direct execution for quick self-test
    from opentrons import simulate
    sim = simulate.get_simulation()
    sim.run_protocol()
