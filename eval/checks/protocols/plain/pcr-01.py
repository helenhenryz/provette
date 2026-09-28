from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup - 8 DNA samples",
    "author": "Lab",
    "description": "20 ul master mix + 5 ul DNA sample per reaction, 8 reactions in a 96-well PCR plate.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

NUM_SAMPLES = 8
MM_VOL = 20
SAMPLE_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1, "Tube rack: master mix + samples")
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "PCR plate")
    tips300 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tips20 = protocol.load_labware("opentrons_96_filtertiprack_20ul", 5)

    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    # Layout: master mix in A1, samples in row B (B1-B6) and C1-C2
    master_mix = tubes["A1"]
    sample_tubes = [tubes[w] for w in ["B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2"]]
    dest_wells = pcr_plate.columns()[0]  # A1-H1

    # Liquids
    mm_liquid = protocol.define_liquid(
        name="PCR master mix",
        description="PCR master mix (polymerase, buffer, dNTPs, primers), enough for 8 reactions + 25% overage",
        display_color="#1F77B4",
    )
    master_mix.load_liquid(mm_liquid, volume=200)

    colors = ["#E41A1C", "#FF7F00", "#4DAF4A", "#984EA3", "#A65628", "#F781BF", "#999999", "#17BECF"]
    for i, tube in enumerate(sample_tubes):
        liq = protocol.define_liquid(
            name=f"DNA sample {i + 1}",
            description=f"DNA template, sample {i + 1}",
            display_color=colors[i],
        )
        tube.load_liquid(liq, volume=50)

    # 1. Master mix into every reaction well (empty wells, so one tip)
    p300.pick_up_tip()
    for well in dest_wells:
        p300.aspirate(MM_VOL, master_mix.bottom(1.5), rate=0.5)
        p300.dispense(MM_VOL, well.bottom(1), rate=0.5)
        p300.blow_out(well.top(-2))
        p300.touch_tip(well, v_offset=-2)
    p300.drop_tip()

    # 2. Samples, fresh tip each, mix in the reaction
    for src, dest in zip(sample_tubes, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(SAMPLE_VOL, src.bottom(1.5))
        p20.dispense(SAMPLE_VOL, dest.bottom(1))
        p20.mix(3, 15, dest.bottom(1))
        p20.blow_out(dest.top(-2))
        p20.drop_tip()

    protocol.comment("PCR setup complete. Seal the plate, spin down briefly and move to the thermocycler.")
