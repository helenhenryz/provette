from opentrons import protocol_api

metadata = {"protocolName": "SDS-PAGE Sample Prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    src_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    dye_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids
    dye = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#FF6600")
    sample_1 = protocol.define_liquid(name="sample 1", description="Protein sample 1", display_color="#FF0000")
    sample_2 = protocol.define_liquid(name="sample 2", description="Protein sample 2", display_color="#FF0011")
    sample_3 = protocol.define_liquid(name="sample 3", description="Protein sample 3", display_color="#FF0022")
    sample_4 = protocol.define_liquid(name="sample 4", description="Protein sample 4", display_color="#FF0033")
    sample_5 = protocol.define_liquid(name="sample 5", description="Protein sample 5", display_color="#FF0044")
    sample_6 = protocol.define_liquid(name="sample 6", description="Protein sample 6", display_color="#FF0055")
    sample_7 = protocol.define_liquid(name="sample 7", description="Protein sample 7", display_color="#FF0066")
    sample_8 = protocol.define_liquid(name="sample 8", description="Protein sample 8", display_color="#FF0077")
    sample_9 = protocol.define_liquid(name="sample 9", description="Protein sample 9", display_color="#FF0088")
    sample_10 = protocol.define_liquid(name="sample 10", description="Protein sample 10", display_color="#FF0099")
    sample_11 = protocol.define_liquid(name="sample 11", description="Protein sample 11", display_color="#FF00AA")
    sample_12 = protocol.define_liquid(name="sample 12", description="Protein sample 12", display_color="#FF00BB")

    # Load liquids into source wells
    src_plate["A1"].load_liquid(liquid="sample 1", volume=50)
    src_plate["A2"].load_liquid(liquid="sample 2", volume=50)
    src_plate["A3"].load_liquid(liquid="sample 3", volume=50)
    src_plate["A4"].load_liquid(liquid="sample 4", volume=50)
    src_plate["A5"].load_liquid(liquid="sample 5", volume=50)
    src_plate["A6"].load_liquid(liquid="sample 6", volume=50)
    src_plate["A7"].load_liquid(liquid="sample 7", volume=50)
    src_plate["A8"].load_liquid(liquid="sample 8", volume=50)
    src_plate["A9"].load_liquid(liquid="sample 9", volume=50)
    src_plate["A10"].load_liquid(liquid="sample 10", volume=50)
    src_plate["A11"].load_liquid(liquid="sample 11", volume=50)
    src_plate["A12"].load_liquid(liquid="sample 12", volume=50)
    dye_plate["A1"].load_liquid(liquid="dye", volume=150)

    # Transfer samples and dye to destination plate
    for i in range(1,13):
        p20.pick_up_tip()
        # Transfer 15 µL of sample i
        p20.aspirate(15, src_plate[f"A{i}"])
        p20.dispense(15, dest_plate[f"A{i}"])
        # Transfer 5 µL of dye
        p20.aspirate(5, dye_plate["A1"])
        p20.dispense(5, dest_plate[f"A{i}"])
        p20.drop_tip()
