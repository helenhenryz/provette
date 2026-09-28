from opentrons import protocol_api

metadata = {"protocolName": "PCR assembly", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="buffer mix", display_color="#000000")
    polymerase = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#800080")
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#0000FF")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    sample_1 = protocol.define_liquid(name="sample 1", description="Sample 1 template", display_color="#FF0000")
    sample_2 = protocol.define_liquid(name="sample 2", description="Sample 2 template", display_color="#FF0000")
    sample_3 = protocol.define_liquid(name="sample 3", description="Sample 3 template", display_color="#FF0000")
    sample_4 = protocol.define_liquid(name="sample 4", description="Sample 4 template", display_color="#FF0000")
    sample_5 = protocol.define_liquid(name="sample 5", description="Sample 5 template", display_color="#FF0000")
    sample_6 = protocol.define_liquid(name="sample 6", description="Sample 6 template", display_color="#FF0000")
    sample_7 = protocol.define_liquid(name="sample 7", description="Sample 7 template", display_color="#FF0000")
    sample_8 = protocol.define_liquid(name="sample 8", description="Sample 8 template", display_color="#FF0000")
    sample_9 = protocol.define_liquid(name="sample 9", description="Sample 9 template", display_color="#FF0000")
    sample_10 = protocol.define_liquid(name="sample 10", description="Sample 10 template", display_color="#FF0000")
    sample_11 = protocol.define_liquid(name="sample 11", description="Sample 11 template", display_color="#FF0000")
    sample_12 = protocol.define_liquid(name="sample 12", description="Sample 12 template", display_color="#FF0000")

    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=buffer, volume=150)      # buffer
    tuberack["A2"].load_liquid(liquid=polymerase, volume=60)   # polymerase
    tuberack["A3"].load_liquid(liquid=fwd_primer, volume=12)   # fwd primer
    tuberack["A4"].load_liquid(liquid=rev_primer, volume=12)   # rev primer
    tuberack["A5"].load_liquid(liquid=water, volume=150)      # water
    tuberack["A6"].load_liquid(liquid=sample_1, volume=10)    # sample 1
    tuberack["B1"].load_liquid(liquid=sample_2, volume=10)    # sample 2
    tuberack["B2"].load_liquid(liquid=sample_3, volume=10)    # sample 3
    tuberack["B3"].load_liquid(liquid=sample_4, volume=10)    # sample 4
    tuberack["B4"].load_liquid(liquid=sample_5, volume=10)    # sample 5
    tuberack["C1"].load_liquid(liquid=sample_6, volume=10)    # sample 6
    tuberack["C2"].load_liquid(liquid=sample_7, volume=10)    # sample 7
    tuberack["C3"].load_liquid(liquid=sample_8, volume=10)    # sample 8
    tuberack["C4"].load_liquid(liquid=sample_9, volume=10)    # sample 9
    tuberack["D1"].load_liquid(liquid=sample_10, volume=10)   # sample 10
    tuberack["D2"].load_liquid(liquid=sample_11, volume=10)   # sample 11
    tuberack["D3"].load_liquid(liquid=sample_12, volume=10)   # sample 12

    # Combine forward primer and reverse primer into polymerase well to create master mix
    p20.pick_up_tip()
    p20.aspirate(12, tuberack["A3"])
    p20.dispense(12, tuberack["A2"])
    p20.drop_tip()

    p20.pick_up_tip()
    p20.aspirate(12, tuberack["A4"])
    p20.dispense(12, tuberack["A2"])
    p20.drop_tip()

    # Mix master mix (use 20 ul since p20 tip holds max 20 ul)
    p20.pick_up_tip()
    p20.mix(5, 20, tuberack["A2"])
    p20.drop_tip()

    # Sample order: 12 reactions, each to a distinct well
    sample_well_names = ["A1","A2","A3","A4","A5","A6","A7","A8","B1","B2","B3","B4"]
    sample_tuberack_wells = ["A6","B1","B2","B3","B4","C1","C2","C3","C4","D1","D2","D3"]

    # Perform PCR assembly
    for i in range(12):
        p20.pick_up_tip()
        # 10 ul buffer mix
        p20.aspirate(10, tuberack["A1"])
        p20.dispense(10, plate[sample_well_names[i]])
        # 2.5 ul master mix
        p20.aspirate(2.5, tuberack["A2"])
        p20.dispense(2.5, plate[sample_well_names[i]])
        # 10.5 ul water
        p20.aspirate(10.5, tuberack["A5"])
        p20.dispense(10.5, plate[sample_well_names[i]])
        # 2 ul template
        p20.aspirate(2, tuberack[sample_tuberack_wells[i]])
        p20.dispense(2, plate[sample_well_names[i]])
        # Drop tip
        p20.drop_tip()
