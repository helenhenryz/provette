from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Assembly",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 2)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips_1000])
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)

    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="PCR buffer", display_color="#0000FF")
    polymerase = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#FF0000")
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#0000FF")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    samples = {}
    for i in range(1, 13):
        samples[i] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i} template", display_color=f"#{i:06X}")

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=buffer, volume=200)
    tubes["A2"].load_liquid(liquid=polymerase, volume=30)
    tubes["A3"].load_liquid(liquid=fwd_primer, volume=20)
    tubes["A4"].load_liquid(liquid=rev_primer, volume=20)
    tubes["A5"].load_liquid(liquid=water, volume=200)

    # Sample wells mapping
    sample_well_names = ["A6", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "C4", "C5"]
    for i in range(1, 13):
        tubes[sample_well_names[i-1]].load_liquid(liquid=samples[i], volume=10)

    # Prepare master mix in tube A7
    p1000.pick_up_tip()
    p1000.aspirate(13.2, tubes["A3"]); p1000.dispense(13.2, tubes["A7"])
    p1000.aspirate(6.6, tubes["A2"]); p1000.dispense(6.6, tubes["A7"])
    p1000.aspirate(13.2, tubes["A4"]); p1000.dispense(13.2, tubes["A7"])
    p1000.aspirate(138.6, tubes["A5"]); p1000.dispense(138.6, tubes["A7"])
    # Mix master mix
    for _ in range(5):
        p1000.aspirate(10, tubes["A7"])
        p1000.dispense(10, tubes["A7"])
    p1000.drop_tip()

    # Assemble PCR reactions
    for i in range(1, 13):
        p20.pick_up_tip()
        # Buffer 10 ul
        p20.aspirate(10, tubes["A1"])
        p20.dispense(10, plate[f"A{i}"])
        # Sample 2 ul
        sample_source = sample_well_names[i-1]
        p20.aspirate(2, tubes[sample_source])
        p20.dispense(2, plate[f"A{i}"])
        # Master mix 13 ul
        p20.aspirate(13, tubes["A7"])
        p20.dispense(13, plate[f"A{i}"])
        p20.drop_tip()

    # No‑template control (well H1)
    p20.pick_up_tip()
    p20.aspirate(10, tubes["A1"])
    p20.dispense(10, plate["H1"])
    p20.aspirate(13, tubes["A7"])
    p20.dispense(13, plate["H1"])
    p20.drop_tip()
