from opentrons import protocol_api

metadata = {
    "protocolName": "PCR assembly from components - 12 samples",
    "description": "Builds a master mix from the components, then 23 ul mix + 2 ul template",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 12
N_MM = 14  # reactions' worth of master mix (2 extra as overage)
PER_RXN = {"buffer": 10, "pol": 0.5, "fwd": 1, "rev": 1, "water": 10.5}
MM_PER_RXN = 23
TEMPLATE_VOL = 2


def run(protocol: protocol_api.ProtocolContext):
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    block = protocol.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("opentrons_96_aluminumblock_nest_wellplate_100ul", 1)
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    buffer_t, pol_t, fwd_t, rev_t, water_t, mm_t = (
        block["A1"], block["B1"], block["C1"], block["D1"], block["A2"], block["B2"])
    # B2 starts as an EMPTY 1.5 ml tube for the master mix
    for well, name, desc, vol, colour in [
        (buffer_t, "Buffer mix", "PCR buffer mix", 200, "#1f77b4"),
        (pol_t, "Polymerase", "DNA polymerase", 20, "#d62728"),
        (fwd_t, "Forward primer", "Forward primer", 30, "#9467bd"),
        (rev_t, "Reverse primer", "Reverse primer", 30, "#8c564b"),
        (water_t, "Water", "Nuclease-free water", 500, "#aec7e8"),
    ]:
        well.load_liquid(protocol.define_liquid(name, desc, colour), vol)

    templates = block.wells()[8:8 + N]  # A3..D5
    for i, t in enumerate(templates):
        t.load_liquid(protocol.define_liquid(
            f"Template {i + 1}", f"Template DNA {i + 1}", "#2ca02c"), 20)

    dests = plate.wells()[:N]  # A1-H1, A2-D2

    # --- Master mix ---
    # p300 tip #1: water into the empty tube, then buffer. The tip has only seen
    # water when it enters the buffer tube, and it dispenses above the liquid.
    p300.pick_up_tip()
    p300.aspirate(PER_RXN["water"] * N_MM, water_t.bottom(2))
    p300.dispense(PER_RXN["water"] * N_MM, mm_t.bottom(3))
    p300.blow_out(mm_t.top(-5))
    p300.aspirate(PER_RXN["buffer"] * N_MM, buffer_t.bottom(2))
    p300.dispense(PER_RXN["buffer"] * N_MM, mm_t.top(-15))
    p300.blow_out(mm_t.top(-5))
    # keep this tip on the p300: it will mix and distribute the master mix

    # Small components: one p20 tip each (separate stocks must stay clean)
    for src, key in [(fwd_t, "fwd"), (rev_t, "rev"), (pol_t, "pol")]:
        vol = PER_RXN[key] * N_MM
        p20.pick_up_tip()
        if key == "pol":
            p20.flow_rate.aspirate = 3
            p20.flow_rate.dispense = 3
        p20.aspirate(vol, src.bottom(1))
        p20.dispense(vol, mm_t.bottom(3))
        p20.mix(2, 10, mm_t.bottom(3))
        p20.blow_out(mm_t.top(-5))
        p20.drop_tip()
    p20.flow_rate.aspirate = 7.56
    p20.flow_rate.dispense = 7.56

    # Mix and distribute the master mix with the same p300 tip (into empty wells)
    p300.mix(8, 200, mm_t.bottom(2))
    for d in dests:
        p300.aspirate(MM_PER_RXN, mm_t.bottom(1.5))
        p300.dispense(MM_PER_RXN, d.bottom(1))
        p300.blow_out(d.top(-2))
    p300.drop_tip()

    # --- Templates: fresh tip each ---
    for t, d in zip(templates, dests):
        p20.pick_up_tip()
        p20.aspirate(TEMPLATE_VOL, t.bottom(1))
        p20.dispense(TEMPLATE_VOL, d.bottom(1))
        p20.mix(3, 15, d.bottom(1))
        p20.blow_out(d.top(-2))
        p20.drop_tip()
