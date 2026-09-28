from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR setup - 6 cDNA samples in triplicate",
    "author": "Lab",
    "description": "10 ul SYBR reactions: 8 ul master mix (with primers) + 2 ul cDNA, 6 samples x 3 replicates.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

NUM_SAMPLES = 6
REPLICATES = 3
MM_VOL = 8
CDNA_VOL = 2


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    strip_block = protocol.load_labware(
        "opentrons_96_aluminumblock_generic_pcr_strip_200ul", 1, "cDNA strip tubes on aluminium block"
    )
    mm_rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap", 2, "Master mix tube rack"
    )
    qpcr_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3, "qPCR plate")
    tips20 = [protocol.load_labware("opentrons_96_filtertiprack_20ul", s) for s in (4, 5)]

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=tips20)

    master_mix = mm_rack["A1"]
    cdna_tubes = strip_block.columns()[0][:NUM_SAMPLES]  # A1-F1

    # Liquids
    mm_liquid = protocol.define_liquid(
        name="SYBR master mix with primers",
        description="2x SYBR Green master mix + primers + water; 18 reactions x 8 ul + ~25% overage",
        display_color="#2CA02C",
    )
    master_mix.load_liquid(mm_liquid, volume=180)

    colors = ["#E41A1C", "#FF7F00", "#377EB8", "#984EA3", "#A65628", "#F781BF"]
    for i, tube in enumerate(cdna_tubes):
        liq = protocol.define_liquid(
            name=f"cDNA sample {i + 1}",
            description=f"cDNA, sample {i + 1}",
            display_color=colors[i],
        )
        tube.load_liquid(liq, volume=20)

    # Layout: sample n in row n (A-F), replicates in columns 1-3
    replicate_wells = [qpcr_plate.rows()[i][:REPLICATES] for i in range(NUM_SAMPLES)]

    # 1. Master mix to all 18 wells, one tip (wells are empty)
    p20.pick_up_tip()
    for wells in replicate_wells:
        for well in wells:
            p20.aspirate(MM_VOL, master_mix.bottom(1.5), rate=0.5)
            p20.dispense(MM_VOL, well.bottom(1), rate=0.5)
            p20.blow_out(well.top(-3))
            p20.touch_tip(well, v_offset=-3)
    p20.drop_tip()

    # 2. cDNA, fresh tip for every well, gentle mix
    for src, wells in zip(cdna_tubes, replicate_wells):
        for well in wells:
            p20.pick_up_tip()
            p20.aspirate(CDNA_VOL, src.bottom(1))
            p20.dispense(CDNA_VOL, well.bottom(1))
            p20.mix(3, 6, well.bottom(1), rate=0.5)
            p20.blow_out(well.top(-3))
            p20.drop_tip()

    protocol.comment("qPCR plate ready. Seal with optical film and spin down before running.")
