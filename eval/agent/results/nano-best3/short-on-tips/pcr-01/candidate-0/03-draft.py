from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_8samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tubes_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)

    # Load instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])

    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    sample_1 = protocol.define_liquid(name="sample 1", description="DNA sample 1", display_color="#0000FF")
    sample_2 = protocol.define_liquid(name="sample 2", description="DNA sample 2", display_color="#001100")
    sample_3 = protocol.define_liquid(name="sample 3", description="DNA sample 3", display_color="#222222")
    sample_4 = protocol.define_liquid(name="sample 4", description="DNA sample 4", display_color="#444444")
    sample_5 = protocol.define_liquid(name="sample 5", description="DNA sample 5", display_color="#666666")
    sample_6 = protocol.define_liquid(name="sample 6", description="DNA sample 6", display_color="#888888")
    sample_7 = protocol.define_liquid(name="sample 7", description="DNA sample 7", display_color="#AAAAAA")
    sample_8 = protocol.define_liquid(name="sample 8", description="DNA sample 8", display_color="#BBBBBB")

    # Load liquids into source wells
    tubes_rack["A1"].load_liquid(liquid=master_mix, volume=200)  # enough for 8*20=160 ul
    tubes_rack["A2"].load_liquid(liquid=sample_1, volume=20)
    tubes_rack["A3"].load_liquid(liquid=sample_2, volume=20)
    tubes_rack["A4"].load_liquid(liquid=sample_3, volume=20)
    tubes_rack["A5"].load_liquid(liquid=sample_4, volume=20)
    tubes_rack["A6"].load_liquid(liquid=sample_5, volume=20)
    tubes_rack["B1"].load_liquid(liquid=sample_6, volume=20)
    tubes_rack["B2"].load_liquid(liquid=sample_7, volume=20)
    tubes_rack["B3"].load_liquid(liquid=sample_8, volume=20)

    # Aspirate master mix and dispense 20 ul into each of the 8 plate wells (A1-A8)
    p300.pick_up_tip()
    p300.aspirate(160, tubes_rack["A1"])
    for i in range(1, 9):
        p300.dispense(20, plate[f"A{i}"])
    p300.drop_tip()

    # Add sample and mix
    for i in range(1, 9):
        # Determine source well for sample i
        if i <= 5:
            src_well = tubes_rack[f"A{i+1}"]
        elif i == 6:
            src_well = tubes_rack["B1"]
        elif i == 7:
            src_well = tubes_rack["B2"]
        elif i == 8:
            src_well = tubes_rack["B3"]
        # Pick up tip, aspirate sample, dispense, mix, drop tip
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, plate[f"A{i}"])
        # Mix the well with full volume 20 ul, 5 times
        p20.mix(5, 20, plate[f"A{i}"])
        p20.drop_tip()
