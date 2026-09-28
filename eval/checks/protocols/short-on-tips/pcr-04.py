from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR setup - 6 cDNA samples in triplicate",
    "description": "8 ul SYBR master mix + 2 ul cDNA, 10 ul reactions",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_SAMPLES = 6
REPS = 3
MM_VOL = 8
CDNA_VOL = 2


def run(protocol: protocol_api.ProtocolContext):
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 6)
    strips = protocol.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", 2)
    mm_rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", 5)
    qpcr = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    mm_tube = mm_rack["A1"]
    mm = protocol.define_liquid("SYBR master mix", "SYBR master mix with primers", "#1f77b4")
    mm_tube.load_liquid(mm, 200)  # 18 x 8 ul = 144 ul + overage

    samples = strips.columns()[0][:N_SAMPLES]  # A1-F1 of the strip
    for i, s in enumerate(samples):
        liq = protocol.define_liquid(f"cDNA sample {i + 1}", f"cDNA sample {i + 1}", "#2ca02c")
        s.load_liquid(liq, 20)

    # sample i -> row i, columns 1-3
    dests = [[qpcr.rows()[i][r] for r in range(REPS)] for i in range(N_SAMPLES)]

    # 1) Master mix into empty wells with ONE tip
    p20.pick_up_tip()
    for row in dests:
        for d in row:
            p20.aspirate(MM_VOL, mm_tube.bottom(2))
            p20.dispense(MM_VOL, d.bottom(1))
            p20.blow_out(d.top(-2))
    p20.drop_tip()

    # 2) cDNA: one tip per sample. The whole triplicate volume is aspirated once
    #    so the tip never goes back into the cDNA tube after touching master mix.
    for s, row in zip(samples, dests):
        p20.pick_up_tip()
        p20.aspirate(CDNA_VOL * REPS + 1, s.bottom(1))  # +1 ul disposal volume
        for d in row:
            p20.dispense(CDNA_VOL, d.bottom(1))
            p20.touch_tip(d, v_offset=-2, speed=20)
        p20.drop_tip()  # disposal volume goes out with the tip
