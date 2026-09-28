from opentrons import protocol_api

metadata = {"protocolName": "Bradford assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)  # Use deep plate for larger volume

    # Load instruments
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Define liquids
    bradford = protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000")
    standard_1 = protocol.define_liquid(name="standard 1", description="BSA standard 1", display_color="#FFFFFF")
    standard_2 = protocol.define_liquid(name="standard 2", description="BSA standard 2", display_color="#FFFFFF")
    standard_3 = protocol.define_liquid(name="standard 3", description="BSA standard 3", display_color="#FFFFFF")
    standard_4 = protocol.define_liquid(name="standard 4", description="BSA standard 4", display_color="#FFFFFF")
    standard_5 = protocol.define_liquid(name="standard 5", description="BSA standard 5", display_color="#FFFFFF")
    standard_6 = protocol.define_liquid(name="standard 6", description="BSA standard 6", display_color="#FFFFFF")
    standard_7 = protocol.define_liquid(name="standard 7", description="BSA standard 7", display_color="#FFFFFF")
    standard_8 = protocol.define_liquid(name="standard 8", description="BSA standard 8", display_color="#FFFFFF")
    sample_1 = protocol.define_liquid(name="sample 1", description="Protein sample 1", display_color="#808080")
    sample_2 = protocol.define_liquid(name="sample 2", description="Protein sample 2", display_color="#808080")
    sample_3 = protocol.define_liquid(name="sample 3", description="Protein sample 3", display_color="#808080")
    sample_4 = protocol.define_liquid(name="sample 4", description="Protein sample 4", display_color="#808080")
    sample_5 = protocol.define_liquid(name="sample 5", description="Protein sample 5", display_color="#808080")
    sample_6 = protocol.define_liquid(name="sample 6", description="Protein sample 6", display_color="#808080")
    sample_7 = protocol.define_liquid(name="sample 7", description="Protein sample 7", display_color="#808080")
    sample_8 = protocol.define_liquid(name="sample 8", description="Protein sample 8", display_color="#808080")
    sample_9 = protocol.define_liquid(name="sample 9", description="Protein sample 9", display_color="#808080")
    sample_10 = protocol.define_liquid(name="sample 10", description="Protein sample 10", display_color="#808080")
    sample_11 = protocol.define_liquid(name="sample 11", description="Protein sample 11", display_color="#808080")
    sample_12 = protocol.define_liquid(name="sample 12", description="Protein sample 12", display_color="#808080")
    sample_13 = protocol.define_liquid(name="sample 13", description="Protein sample 13", display_color="#808080")
    sample_14 = protocol.define_liquid(name="sample 14", description="Protein sample 14", display_color="#808080")
    sample_15 = protocol.define_liquid(name="sample 15", description="Protein sample 15", display_color="#808080")
    sample_16 = protocol.define_liquid(name="sample 16", description="Protein sample 16", display_color="#808080")
    sample_17 = protocol.define_liquid(name="sample 17", description="Protein sample 17", display_color="#808080")
    sample_18 = protocol.define_liquid(name="sample 18", description="Protein sample 18", display_color="#808080")
    sample_19 = protocol.define_liquid(name="sample 19", description="Protein sample 19", display_color="#808080")
    sample_20 = protocol.define_liquid(name="sample 20", description="Protein sample 20", display_color="#808080")

    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=bradford, volume=12000)
    plate["D5"].load_liquid(liquid=standard_1, volume=150)
    plate["D6"].load_liquid(liquid=standard_2, volume=150)
    plate["D7"].load_liquid(liquid=standard_3, volume=150)
    plate["D8"].load_liquid(liquid=standard_4, volume=150)
    plate["D9"].load_liquid(liquid=standard_5, volume=150)
    plate["D10"].load_liquid(liquid=standard_6, volume=150)
    plate["D11"].load_liquid(liquid=standard_7, volume=150)
    plate["D12"].load_liquid(liquid=standard_8, volume=150)
    tubes["A1"].load_liquid(liquid=sample_1, volume=100)
    tubes["A2"].load_liquid(liquid=sample_2, volume=100)
    tubes["A3"].load_liquid(liquid=sample_3, volume=100)
    tubes["A4"].load_liquid(liquid=sample_4, volume=100)
    tubes["A5"].load_liquid(liquid=sample_5, volume=100)
    tubes["A6"].load_liquid(liquid=sample_6, volume=100)
    tubes["B1"].load_liquid(liquid=sample_7, volume=100)
    tubes["B2"].load_liquid(liquid=sample_8, volume=100)
    tubes["B3"].load_liquid(liquid=sample_9, volume=100)
    tubes["B4"].load_liquid(liquid=sample_10, volume=100)
    tubes["B5"].load_liquid(liquid=sample_11, volume=100)
    tubes["B6"].load_liquid(liquid=sample_12, volume=100)
    tubes["C1"].load_liquid(liquid=sample_13, volume=100)
    tubes["C2"].load_liquid(liquid=sample_14, volume=100)
    tubes["C3"].load_liquid(liquid=sample_15, volume=100)
    tubes["C4"].load_liquid(liquid=sample_16, volume=100)
    tubes["C5"].load_liquid(liquid=sample_17, volume=100)
    tubes["C6"].load_liquid(liquid=sample_18, volume=100)
    tubes["D1"].load_liquid(liquid=sample_19, volume=100)
    tubes["D2"].load_liquid(liquid=sample_20, volume=100)

    # Define sample destinations and standard wells
    sample_destinations = [
        "A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12",
        "B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12",
        "C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11","C12",
        "D1","D2","D3","D4"
    ]
    standard_wells = ["D5","D6","D7","D8","D9","D10","D11","D12"]
    all_used_wells = sample_destinations + standard_wells

    # Sample addition with p20
    sample_to_tube = {
        1: "A1", 2: "A2", 3: "A3", 4: "A4", 5: "A5", 6: "A6",
        7: "B1", 8: "B2", 9: "B3", 10: "B4", 11: "B5", 12: "B6",
        13: "C1", 14: "C2", 15: "C3", 16: "C4", 17: "C5", 18: "C6",
        19: "D1", 20: "D2"
    }
    for i in range(20):
        src = sample_to_tube[i+1]
        dest1 = sample_destinations[2*i]
        dest2 = sample_destinations[2*i+1]
        p20.pick_up_tip()
        p20.aspirate(5, tubes[src])
        p20.dispense(5, plate[dest1])
        p20.aspirate(5, tubes[src])
        p20.dispense(5, plate[dest2])
        p20.drop_tip()

    # Bradford addition with p300
    p300.pick_up_tip()
    for well_name in all_used_wells:
        p300.aspirate(250, reservoir["A1"])
        p300.dispense(250, plate[well_name])
    p300.drop_tip()
