from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup - 24 gDNA samples, 25 ul reactions",
    "author": "Lab",
    "description": "12.5 ul 2x master mix (with primers) + 10.5 ul water + 2 ul gDNA per reaction.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_SAMPLES = 24
MM_VOL = 12.5
WATER_VOL = 10.5
DNA_VOL = 2.0


def run(protocol: protocol_api.ProtocolContext):
    tips_a = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    tips_b = protocol.load_labware("opentrons_96_filtertiprack_20ul", 2)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3, "PCR plate")
    sample_rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 4, "gDNA samples")
    reagent_rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 5, "Reagents")

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_a, tips_b])

    master_mix = reagent_rack["A1"]
    water = reagent_rack["B1"]

    # Liquids
    mm_liq = protocol.define_liquid("2x PCR master mix", "2x master mix with primers", "#D62728")
    water_liq = protocol.define_liquid("Water", "Nuclease-free water", "#1F77B4")
    master_mix.load_liquid(mm_liq, 400)   # 300 ul needed
    water.load_liquid(water_liq, 1000)    # 252 ul needed

    samples = sample_rack.wells()[:N_SAMPLES]
    for i, tube in enumerate(samples):
        liq = protocol.define_liquid(
            f"gDNA sample {i + 1}", f"Genomic DNA sample {i + 1}", "#2CA02C")
        tube.load_liquid(liq, 50)

    # Reactions fill rows A-B-C... column-wise: sample n -> n-th well (A1, B1, ... H3)
    dests = pcr_plate.wells()[:N_SAMPLES]

    # 1. Water into empty wells, one tip
    p20.pick_up_tip()
    for d in dests:
        p20.aspirate(WATER_VOL, water)
        p20.dispense(WATER_VOL, d)
        p20.blow_out(d.top(-2))
    p20.drop_tip()

    # 2. Master mix, fresh tip per well (tip touches the water), pipetted slowly (viscous)
    for d in dests:
        p20.pick_up_tip()
        p20.aspirate(MM_VOL, master_mix, rate=0.5)
        protocol.delay(seconds=1)
        p20.dispense(MM_VOL, d, rate=0.5)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    # 3. DNA, fresh tip per sample, mix the reaction
    for s, d in zip(samples, dests):
        p20.pick_up_tip()
        p20.aspirate(DNA_VOL, s)
        p20.dispense(DNA_VOL, d)
        p20.mix(5, 15, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    protocol.comment("Done. Seal the plate, spin down briefly and load on the thermocycler.")
