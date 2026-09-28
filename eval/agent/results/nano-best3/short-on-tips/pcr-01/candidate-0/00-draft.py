from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_8samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    master_mix = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    sample_1 = protocol.define_liquid(name="sample 1", description="DNA sample 1", display_color="#0000FF")
    sample_2 = protocol.define_liquid(name="sample 2", description="DNA sample 2", display_color="#001100")
    sample_3 = protocol.define_liquid(name="sample 3", description="DNA sample 3", display_color="#222222")
    sample_4 = protocol.define_liquid(name="sample 4", description="DNA sample 4", display_color="#444444")
    sample_5 = protocol.define_liquid(name="sample 5", description="DNA sample 5", display_color="#666666")
    sample_6 = protocol.define_liquid(name="sample 6", description="DNA sample 6", display_color="#888888")
    sample_7 = protocol.define_liquid(name="sample 7", description="DNA sample 7", display_color="#AAAAAA")
    sample_8 = protocol.define_liquid(name="sample 8", description="DNA sample 8", display_color="#BBBBBB")

    tubes_rack["A1"].load_liquid(liquid=master_mix, volume=200)
    tubes_rack["A2"].load_liquid(liquid=sample_1, volume=20)
    tubes_rack["A3"].load_liquid(liquid=sample_2, volume=20)
    tubes_rack["A4"].load_liquid(liquid=sample_3, volume=20)
    tubes_rack["A5"].load_liquid(liquid=sample_4, volume=20)
    tubes_rack["A6"].load_liquid(liquid=sample_5, volume=20)
    tubes_rack["B1"].load_liquid(liquid=sample_6, volume=20)
    tubes_rack["B2"].load_liquid(liquid=sample_7, volume=20)
    tubes_rack["B3"].load_liquid(liquid=sample_8, volume=20)

    sample_well_map = {
        1: tubes_rack["A2"],
        2: tubes_rack["A3"],
        3: tubes_rack["A4"],
        4: tubes_rack["A5"],
        5: tubes_rack["A6"],
        6: tubes_rack["B1"],
        7: tubes_rack["B2"],
        8: tubes_rack["B3"]
    }

    p300.pick_up_tip()
    p300.aspirate(160, tubes_rack["A1"])
    for i in range(1, 9):
        p300.dispense(20, plate[f"A{i}"])
    for i in range(1, 9):
        p300.aspirate(5, sample_well_map[i])
        p300.dispense(5, plate[f"A{i}"])
    p300.drop_tip()
