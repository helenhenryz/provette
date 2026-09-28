from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_8samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20ul])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    sample_1 = protocol.define_liquid(
        name="sample 1", description="DNA sample 1", display_color="#00FF00"
    )
    sample_2 = protocol.define_liquid(
        name="sample 2", description="DNA sample 2", display_color="#0000FF"
    )
    sample_3 = protocol.define_liquid(
        name="sample 3", description="DNA sample 3", display_color="#FFFF00"
    )
    sample_4 = protocol.define_liquid(
        name="sample 4", description="DNA sample 4", display_color="#FF00FF"
    )
    sample_5 = protocol.define_liquid(
        name="sample 5", description="DNA sample 5", display_color="#00FFFF"
    )
    sample_6 = protocol.define_liquid(
        name="sample 6", description="DNA sample 6", display_color="#800000"
    )
    sample_7 = protocol.define_liquid(
        name="sample 7", description="DNA sample 7", display_color="#808000"
    )
    sample_8 = protocol.define_liquid(
        name="sample 8", description="DNA sample 8", display_color="#008080"
    )

    # Load liquids into tube rack wells
    tubes["A1"].load_liquid(liquid=master_mix, volume=1000)
    tubes["B1"].load_liquid(liquid=sample_1, volume=500)
    tubes["C1"].load_liquid(liquid=sample_2, volume=500)
    tubes["D1"].load_liquid(liquid=sample_3, volume=500)
    tubes["A2"].load_liquid(liquid=sample_4, volume=500)
    tubes["B2"].load_liquid(liquid=sample_5, volume=500)
    tubes["C2"].load_liquid(liquid=sample_6, volume=500)
    tubes["D2"].load_liquid(liquid=sample_7, volume=500)
    tubes["A3"].load_liquid(liquid=sample_8, volume=500)

    # Define reaction wells and sample wells
    reaction_wells = ["A1","A2","A3","A4","A5","A6","A7","A8"]
    sample_wells = ["B1","C1","D1","A2","B2","C2","D2","A3"]

    # Transfer master mix and samples to each reaction well
    for i in range(8):
        # Add 20 ul master mix
        p20.pick_up_tip()
        p20.aspirate(20, tubes["A1"])
        p20.dispense(20, plate[reaction_wells[i]])
        p20.drop_tip()
        # Add 5 ul sample
        p20.pick_up_tip()
        p20.aspirate(5, tubes[sample_wells[i]])
        p20.dispense(5, plate[reaction_wells[i]])
        p20.drop_tip()
