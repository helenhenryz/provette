from opentrons import protocol_api

metadata = {
    "protocolName": "Add serum samples and standards to ELISA plate",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Labware ----------
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', 1)          # tips
    src_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)      # serum source plate
    elisa_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 3)    # coated ELISA plate
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 4)  # standards

    # ---------- Pipette ----------
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tiprack])

    # ---------- Define liquids ----------
    # Colors are arbitrary; just need a valid hex string.
    std_color = "#FF0000"
    serum_color = "#0000FF"

    # Standards 1‑8
    for i in range(1, 9):
        protocol.define_liquid(
            name=f"standard {i}",
            description="ELISA standard",
            display_color=std_color
        )

    # Serum samples 1‑40
    for i in range(1, 41):
        protocol.define_liquid(
            name=f"serum {i}",
            description="Patient serum sample",
            display_color=serum_color
        )

    # ---------- Load liquids ----------
    # Load standards into tubes (use first 8 wells of the rack)
    std_tubes = []
    for well in tube_rack.wells():
        std_tubes.append(well)
        if len(std_tubes) == 8:
            break
    for idx, tube in enumerate(std_tubes):
        tube.load_liquid(
            liquid=protocol.get_liquid_by_name(f"standard {idx + 1}"),
            volume=250  # µL, enough for several aspirates
        )

    # Load serum samples into the source plate (wells A1‑H5 → 40 wells)
    for row in "ABCDEFGH":
        for col in range(1, 6):  # columns 1‑5
            src_well = src_plate[f"{row}{col}"]
            src_well.load_liquid(
                liquid=protocol.get_liquid_by_name(f"serum {(int(col-1))*8 + (ord(row)-ord('A')) + 1}"),
                volume=200  # µL initial volume per sample
            )

    # ---------- Transfer serum samples ----------
    for row in "ABCDEFGH":
        for col in range(1, 6):          # columns 1‑5
            src = src_plate[f"{row}{col}"]
            dst = elisa_plate[f"{row}{col}"]
            p300.pick_up_tip()
            p300.aspirate(100, src)
            p300.dispense(100, dst)
            p300.drop_tip()

    # ---------- Transfer standards (column 12 of ELISA plate) ----------
    for idx, tube in enumerate(std_tubes):
        dest_row = chr(ord('A') + idx)   # A‑H
        dst = elisa_plate[f"{dest_row}12"]
        p300.pick_up_tip()
        p300.aspirate(100, tube)         # take standard from tube
        p300.dispense(100, dst)           # add to ELISA plate column 12
        p300.drop_tip()
