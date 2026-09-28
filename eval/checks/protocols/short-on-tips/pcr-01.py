from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup - 8 samples",
    "description": "20 ul master mix + 5 ul sample per reaction, 8 reactions",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_SAMPLES = 8
MM_VOL = 20
SAMPLE_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tubes = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    # Liquids
    mm_tube = tubes["A1"]
    mm = protocol.define_liquid("PCR master mix", "2x master mix with primers", "#1f77b4")
    mm_tube.load_liquid(mm, 200)  # 8 x 20 ul + 25 % overage
    sample_tubes = [tubes.wells()[4 + i] for i in range(N_SAMPLES)]  # A2.. column-wise
    for i, t in enumerate(sample_tubes):
        liq = protocol.define_liquid(f"DNA sample {i + 1}", f"DNA sample {i + 1}", "#2ca02c")
        t.load_liquid(liq, 50)

    dests = plate.columns()[0][:N_SAMPLES]  # A1-H1

    # 1) Master mix into the empty wells: ONE tip for all 8 wells
    p20.pick_up_tip()
    for d in dests:
        p20.aspirate(MM_VOL, mm_tube.bottom(1.5))
        p20.dispense(MM_VOL, d.bottom(1))
        p20.blow_out(d.top(-2))
    p20.drop_tip()

    # 2) Samples: a fresh tip per sample (no cross-contamination), mix in the well
    for s, d in zip(sample_tubes, dests):
        p20.pick_up_tip()
        p20.aspirate(SAMPLE_VOL, s.bottom(1.5))
        p20.dispense(SAMPLE_VOL, d.bottom(1))
        p20.mix(3, 15, d.bottom(1))
        p20.blow_out(d.top(-2))
        p20.drop_tip()
