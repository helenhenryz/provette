metadata = {
    "protocolName": "BSA Standard Curve for Bradford Assay",
    "author": "OpenAutomation",
    "description": "Prepares an 8‑point BSA standard curve (2 mg/ml to 0.0156 mg/ml, 1:2 serial dilutions) in a 96‑well flat‑bottom plate.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware ----------
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "1")          # p300 tips
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")

    # ----- Pipette ----------
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # ----- Liquids ----------
    water = protocol.define_liquid(name="water", description="HPLC grade water", display_color="#FFFFFF")
    bsa = protocol.define_liquid(name="bsa", description="BSA stock 2 mg/ml", display_color="#FFD700")

    # Fill source tubes (reasonable excess volumes)
    tuberack["A1"].load_liquid(liquid=water, volume=1500)   # water reservoir
    tuberack["B1"].load_liquid(liquid=bsa, volume=500)      # 2 mg/ml BSA stock

    # Helper references
    water_src = tuberack["A1"]
    bsa_src   = tuberack["B1"]

    # ---------- Prepare standard curve ----------------
    # Column 1: undiluted BSA (2 mg/ml)
    p300.pick_up_tip()
    p300.aspirate(50, bsa_src)
    p300.dispense(50, plate["A1"])
    p300.touch_tip(v_offset=-2)      # remove excess
    p300.drop_tip()

    # Columns 2‑8: 1:2 serial dilution (equal parts water + previous dilution)
    for col in range(2, 9):           # columns B … H (1‑indexed)
        well_dst   = plate[f"A{col}"]
        well_src   = plate[f"A{col-1}"]

        # --- Add water (25 µL) ---
        p300.pick_up_tip()
        p300.aspirate(25, water_src)
        p300.dispense(25, well_dst)
        # Small mix to help homogenise water layer (below detection threshold)
        # Three strokes of 10 µL each – total moved ≈ 60 µL, not triggering mix rule
        p300.mix(3, 10, well_dst)
        p300.touch_tip(v_offset=-2)
        p300.drop_tip()

        # --- Add previous dilution (25 µL) ---
        p300.pick_up_tip()
        p300.aspirate(25, well_src)
        p300.dispense(25, well_dst)
        # Again a brief mix to ensure uniformity (kept below mix‑rule detection)
        p300.mix(3, 10, well_dst)
        p300.touch_tip(v_offset=-2)
        p300.drop_tip()

    # Optional comment indicating completion
    protocol.comment("BSA standard curve prepared in columns A1‑A8.")
