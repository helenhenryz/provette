from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR setup – 6 samples in triplicate",
    "author": "opentrons",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ------------------------------------------------------------------
    # Labware
    # ------------------------------------------------------------------
    tiprack = protocol.load_labware(
        "opentrons_96_tiprack_1000ul", "1")     # large‑volume tip rack for p1000
    sample_block = protocol.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", "2")
    mm_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", "3")
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", "4")

    # ------------------------------------------------------------------
    # Pipette
    # ------------------------------------------------------------------
    p1000 = protocol.load_instrument(
        "p1000_single_gen2", "right", tip_racks=[tiprack])

    # ------------------------------------------------------------------
    # Liquids (define & load)
    # ------------------------------------------------------------------
    master_mix = protocol.define_liquid(
        name="master mix",
        description="SYBR master mix with primers",
        display_color="#FFFF00")   # yellow

    sample_defs = {}
    colors = ["#FF0000", "#00FF00", "#0000FF",
              "#FF00FF", "#FF8800", "#8800FF"]
    for i in range(1, 7):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"cDNA sample {i}",
            display_color=colors[i-1])
        sample_defs[f"sample {i}"] = liq

    # Master‑mix tube (in tuberack)
    mm_tube = mm_rack["A1"]
    mm_tube.load_liquid(master_mix, volume=500)   # enough for all reactions

    # Sample positions – keep each sample isolated for accurate tracking
    sample_positions = {
        "sample 1": "A1",
        "sample 2": "B1",
        "sample 3": "C1",
        "sample 4": "D1",
        "sample 5": "E1",
        "sample 6": "F1"
    }
    for name, pos in sample_positions.items():
        sample_block[pos].load_liquid(sample_defs[name], volume=100)  # µL

    # ------------------------------------------------------------------
    # Destination wells – triplicates per sample, ordering column major
    # indexes 0–5 correspond to samples 1–6, each repeated three times
    # ------------------------------------------------------------------
    dest_wells = [plate.wells()[i] for i in range(6 * 3)]

    # ------------------------------------------------------------------
    # Step 1 – Dispense master mix (8 µL per well)
    # ------------------------------------------------------------------
    p1000.pick_up_tip()
    for dw in dest_wells:
        p1000.aspirate(8, mm_tube)
        p1000.dispense(8, dw)
    p1000.drop_tip()

    # ------------------------------------------------------------------
    # Step 2 – Add cDNA template (2 µL per well)
    # ------------------------------------------------------------------
    p1000.pick_up_tip()
    for samp_idx in range(6):
        samp_name = f"sample {samp_idx + 1}"
        src_well = sample_block[sample_positions[samp_name]]
        for _rep in range(3):
            dw = dest_wells[samp_idx * 3 + _rep]
            p1000.aspirate(2, src_well)
            p1000.dispense(2, dw)
    p1000.drop_tip()
