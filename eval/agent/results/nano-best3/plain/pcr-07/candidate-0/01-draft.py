from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Assembly",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
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
    tubes["A1"].load_liquid(liquid=buffer, volume=150)
    tubes["A2"].load_liquid(liquid=polymerase, volume=15)
    tubes["A3"].load_liquid(liquid=fwd_primer, volume=20)
    tubes["A4"].load_liquid(liquid=rev_primer, volume=20)
    tubes["A5"].load_liquid(liquid=water, volume=200)
    for i in range(1, 8):
        tubes[f"A{i+5}"].load_liquid(liquid=samples[i], volume=10)
    for i in range(8, 13):
        tubes[f"B{i-7}"].load_liquid(liquid=samples[i], volume=10)

    # Assemble PCR reactions
    for i in range(1, 13):
        # Determine source well for sample i
        if i <= 7:
            sample_source = f"A{i+5}"
        else:
            sample_source = f"B{i-7}"
        # Pick up tip
        p20.pick_up_tip()
        # Transfer buffer (10 ul)
        p20.aspirate(10, tubes["A1"])
        p20.dispense(10, plate[f"A{i}"])
        # Transfer sample (2 ul)
        p20.aspirate(2, tubes[sample_source])
        p20.dispense(2, plate[f"A{i}"])
        # Transfer forward primer (1 ul)
        p20.aspirate(1, tubes["A3"])
        p20.dispense(1, plate[f"A{i}"])
        # Transfer reverse primer (1 ul)
        p20.aspirate(1, tubes["A4"])
        p20.dispense(1, plate[f"A{i}"])
        # Transfer polymerase (0.5 ul) - aspirate 1 ul, dispense 0.5 ul
        p20.aspirate(1, tubes["A2"])
        p20.dispense(0.5, plate[f"A{i}"])
        # Transfer water (10.5 ul)
        p20.aspirate(10.5, tubes["A5"])
        p20.dispense(10.5, plate[f"A{i}"])
        # Drop tip
        p20.drop_tip()
