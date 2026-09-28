from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup - 24 gDNA samples, 25 ul reactions",
    "description": "12.5 ul 2x master mix + 10.5 ul water + 2 ul DNA per well. 25 tips in total.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 24


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    samples = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1, "gDNA samples")
    reagents = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "Reagents")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3, "PCR plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mm_tube = reagents["A1"]
    water_tube = reagents["B1"]

    mm = protocol.define_liquid("2x PCR master mix", "2x master mix with primers", "#1f77b4")
    water = protocol.define_liquid("Water", "Nuclease-free water", "#aec7e8")
    mm_tube.load_liquid(mm, 400)      # 24 x 12.5 = 300 ul needed
    water_tube.load_liquid(water, 500)  # 24 x 10.5 = 252 ul needed
    for i, tube in enumerate(samples.wells()[:N]):
        dna = protocol.define_liquid(f"gDNA sample {i + 1}", f"Genomic DNA sample {i + 1}", "#2ca02c")
        tube.load_liquid(dna, 50)

    dests = plate.wells()[:N]  # A1..H1, A2..H2, A3..H3 (same order as the sample tubes)

    # One tip for both reagents: water first into the empty wells, then the
    # master mix with the same tip (it has only seen water, and no DNA is in
    # the plate yet, so nothing can be carried over).
    p20.pick_up_tip()
    for d in dests:
        p20.aspirate(10.5, water_tube)
        p20.dispense(10.5, d)
        p20.blow_out(d.bottom(3))
    p20.flow_rate.aspirate = 4   # master mix is viscous
    p20.flow_rate.dispense = 4
    for d in dests:
        p20.aspirate(12.5, mm_tube)
        protocol.delay(seconds=1)
        p20.dispense(12.5, d)
        protocol.delay(seconds=1)
        p20.blow_out(d.bottom(4))
    p20.drop_tip()
    p20.flow_rate.aspirate = 7.56
    p20.flow_rate.dispense = 7.56

    # DNA: a fresh tip per sample is unavoidable; the same tip mixes the reaction.
    for s, d in zip(samples.wells()[:N], dests):
        p20.pick_up_tip()
        p20.aspirate(2, s)
        p20.dispense(2, d)
        p20.mix(3, 15, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    protocol.comment("Seal the plate, spin briefly and transfer to the thermocycler.")
