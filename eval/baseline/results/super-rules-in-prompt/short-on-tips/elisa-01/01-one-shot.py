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

    # ---------- Define liquids & keep handles ----------
    std_color = "#FF0000"
    serum_color = "#0000FF"

    standards = {}      # name -> Liquid
    serums = {}         # name -> Liquid

    # Standards 1‑8
    for i in range(1, 9):
        liq = protocol.define_liquid(
            name=f"standard {i}",
            description="ELISA standard",
            display_color=std_color
        )
        standards[f"standard {i}"] = liq

    # Serum samples 1‑40
    for i in range(1, 41):
        liq = protocol.define_liquid(
            name=f"serum {i}",
            description="Patient serum sample",
            display_color=serum_color
        )
        serums[f"serum {i}"] = liq

    # ---------- Load liquids ----------
    # Load standards into tubes (first 8 wells)
    std_wells = list(tube_rack.wells())[:8]
    for idx, tube in enumerate(std_wells):
        liq_name = f"standard {idx + 1}"
        tube.load_liquid(liquid=standards[liq_name], volume=250)

    # Load serum samples into source plate (rows A-H, cols 1-5 => 40 wells)
    serum_index = 1
    for row in "ABCDEFGH":
        for col in range(1, 6):   # columns 1‑5
            src_well = src_plate[f"{row}{col}"]
            liq_name = f"serum {serum_index}"
            src_well.load_liquid(liquid=serums[liq_name], volume=200)
            serum_index += 1

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
    for idx, tube in enumerate(std_wells):
        dest_row = chr(ord('A') + idx)   # A‑H
        dst = elisa_plate[f"{dest_row}12"]
        p300.pick_up_tip()
        p300.aspirate(100, tube)         # take standard from tube
        p300.dispense(100, dst)           # add to ELISA plate column 12
        p300.drop_tip()
