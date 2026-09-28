from opentrons import protocol_api

metadata = {"protocolName": "Bradford assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 5)

    # Load instruments
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])

    # Define liquids
    bradford = protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000")
    for i in range(1,9):
        std_name = f"standard {i}"
        protocol.define_liquid(name=std_name, description=f"BSA standard {i}", display_color="#FFFFFF")
    for i in range(1,21):
        sample_name = f"sample {i}"
        protocol.define_liquid(name=sample_name, description=f"Protein sample {i}", display_color="#808080")

    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid="bradford", volume=12000)
    plate["D5"].load_liquid(liquid="standard 1", volume=50)
    plate["D6"].load_liquid(liquid="standard 2", volume=50)
    plate["D7"].load_liquid(liquid="standard 3", volume=50)
    plate["D8"].load_liquid(liquid="standard 4", volume=50)
    plate["D9"].load_liquid(liquid="standard 5", volume=50)
    plate["D10"].load_liquid(liquid="standard 6", volume=50)
    plate["D11"].load_liquid(liquid="standard 7", volume=50)
    plate["D12"].load_liquid(liquid="standard 8", volume=50)
    tubes["A1"].load_liquid(liquid="sample 1", volume=100)
    tubes["A2"].load_liquid(liquid="sample 2", volume=100)
    tubes["A3"].load_liquid(liquid="sample 3", volume=100)
    tubes["A4"].load_liquid(liquid="sample 4", volume=100)
    tubes["A5"].load_liquid(liquid="sample 5", volume=100)
    tubes["A6"].load_liquid(liquid="sample 6", volume=100)
    tubes["B1"].load_liquid(liquid="sample 7", volume=100)
    tubes["B2"].load_liquid(liquid="sample 8", volume=100)
    tubes["B3"].load_liquid(liquid="sample 9", volume=100)
    tubes["B4"].load_liquid(liquid="sample 10", volume=100)
    tubes["B5"].load_liquid(liquid="sample 11", volume=100)
    tubes["B6"].load_liquid(liquid="sample 11", volume=100)
    tubes["B7"].load_liquid(liquid="sample 12", volume=100)
    tubes["B7"].load_liquid(liquid="sample 12", volume=100)
    tubes["C1"].load_liquid(liquid="sample 13", volume=100)
    tubes["C2"].load_liquid(liquid="sample 14", volume=100)
    tubes["C3"].load_liquid(liquid="sample 15", volume=100)
    tubes["C4"].load_liquid(liquid="sample 16", volume=100)
    tubes["C5"].load_liquid(liquid="sample 17", volume=100)
    tubes["C6"].load_liquid(liquid="sample 18", volume=100)
    tubes["D1"].load_liquid(liquid="sample 19", volume=100)
    tubes["D2"].load_liquid(liquid="sample 20", volume=100)

    # Define sample destinations and standard wells
    sample_destinations = [
        "A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12",
        "B1","B2","B3","B4","B5","B6","B7","B8","B8","B9","B10","B11","B12",
        "C1","C2","C3","C4","C5","C6","D1","D2","D3","D4"
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
