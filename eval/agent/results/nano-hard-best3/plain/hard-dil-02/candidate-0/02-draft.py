from opentrons import protocol_api

metadata = {"protocolName": "Serial Dilution and Transfer", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids and capture their objects
    compound_1 = protocol.define_liquid(name="compound 1", description="Compound 1 stock", display_color="#FF0000")
    compound_2 = protocol.define_liquid(name="compound 2", description="Compound 2 stock", display_color="#00FF00")
    compound_3 = protocol.define_liquid(name="compound 3", description="Compound 3 stock", display_color="#0000FF")
    compound_4 = protocol.define_liquid(name="compound 4", description="Compound 4 stock", display_color="#FFFF00")
    dmso = protocol.define_liquid(name="dmso", description="DMSO", display_color="#FFFFFF")
    medium = protocol.define_liquid(name="medium", description="Cell culture medium", display_color="#808080")
    
    # Load labware
    plate_dilution = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    plate_assay = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)
    
    # Load liquids into containers
    tubes["A1"].load_liquid(liquid=compound_1, volume=1000)
    tubes["A2"].load_liquid(liquid=compound_2, volume=1000)
    tubes["A3"].load_liquid(liquid=compound_3, volume=1000)
    tubes["A4"].load_liquid(liquid=compound_4, volume=1000)
    reservoir["A1"].load_liquid(liquid=dmso, volume=5000)
    for well in plate_assay.wells():
        well.load_liquid(liquid=medium, volume=90)
    
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])
    
    # Process each compound row with fresh tips to avoid cross‑contamination
    # Row A (compound 1)
    # Well 1
    p300.pick_up_tip()
    p300.aspirate(90, tubes["A1"])
    p300.dispense(90, plate_dilution["A1"])
    p300.mix(10, 20, plate_dilution["A1"])
    p300.drop_tip()
    # Well 2
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["A2"])
    p300.aspirate(30, plate_dilution["A1"])
    p300.dispense(30, plate_dilution["A2"])
    p300.mix(10, 20, plate_dilution["A2"])
    p300.drop_tip()
    # Well 3
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["A3"])
    p300.aspirate(30, plate_dilution["A2"])
    p300.dispense(30, plate_dilution["A3"])
    p300.mix(10, 20, plate_dilution["A3"])
    p300.drop_tip()
    # Well 4
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["A4"])
    p300.aspirate(30, plate_dilution["A3"])
    p300.dispense(30, plate_dilution["A4"])
    p300.mix(10, 20, plate_dilution["A4"])
    p300.drop_tip()
    # Well 5
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["A5"])
    p300.aspirate(30, plate_dilution["A4"])
    p300.dispense(30, plate_dilution["A5"])
    p300.mix(10, 20, plate_dilution["A5"])
    p300.drop_tip()
    # Well 6
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["A6"])
    p300.aspirate(30, plate_dilution["A5"])
    p300.dispense(30, plate_dilution["A6"])
    p300.mix(10, 20, plate_dilution["A6"])
    p300.drop_tip()
    
    # Row B (compound 2)
    # Well 1
    p300.pick_up_tip()
    p300.aspirate(90, tubes["A2"])
    p300.dispense(90, plate_dilution["B1"])
    p300.mix(10, 20, plate_dilution["B1"])
    p300.drop_tip()
    # Well 2
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["B2"])
    p300.aspirate(30, plate_dilution["B1"])
    p300.dispense(30, plate_dilution["B2"])
    p300.mix(10, 20, plate_dilution["B2"])
    p300.drop_tip()
    # Well 3
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["B3"])
    p300.aspirate(30, plate_dilution["B2"])
    p300.dispense(30, plate_dilution["B3"])
    p300.mix(10, 20, plate_dilution["B3"])
    p300.drop_tip()
    # Well 4
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["B4"])
    p300.aspirate(30, plate_dilution["B3"])
    p300.dispense(30, plate_dilution["B4"])
    p300.mix(10, 20, plate_dilution["B4"])
    p300.drop_tip()
    # Well 5
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["B5"])
    p300.aspirate(30, plate_dilution["B4"])
    p300.dispense(30, plate_dilution["B5"])
    p300.mix(10, 20, plate_dilution["B5"])
    p300.drop_tip()
    # Well 6
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["B6"])
    p300.aspirate(30, plate_dilution["B5"])
    p300.dispense(30, plate_dilution["B6"])
    p300.mix(10, 20, plate_dilution["B6"])
    p300.drop_tip()
    
    # Row C (compound 3)
    # Well 1
    p300.pick_up_tip()
    p300.aspirate(90, tubes["A3"])
    p300.dispense(90, plate_dilution["C1"])
    p300.mix(10, 20, plate_dilution["C1"])
    p300.drop_tip()
    # Well 2
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["C2"])
    p300.aspirate(30, plate_dilution["C1"])
    p300.dispense(30, plate_dilution["C2"])
    p300.mix(10, 20, plate_dilution["C2"])
    p300.drop_tip()
    # Well 3
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["C3"])
    p300.aspirate(30, plate_dilution["C2"])
    p300.dispense(30, plate_dilution["C3"])
    p300.mix(10, 20, plate_dilution["C3"])
    p300.drop_tip()
    # Well 4
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["C4"])
    p300.aspirate(30, plate_dilution["C3"])
    p300.dispense(30, plate_dilution["C4"])
    p300.mix(10, 20, plate_dilution["C4"])
    p300.drop_tip()
    # Well 5
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["C5"])
    p300.aspirate(30, plate_dilution["C4"])
    p300.dispense(30, plate_dilution["C5"])
    p300.mix(10, 20, plate_dilution["C5"])
    p300.drop_tip()
    # Well 6
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["C6"])
    p300.aspirate(30, plate_dilution["C5"])
    p300.dispense(30, plate_dilution["C6"])
    p300.mix(10, 20, plate_dilution["C6"])
    p300.drop_tip()
    
    # Row D (compound 4)
    # Well 1
    p300.pick_up_tip()
    p300.aspirate(90, tubes["A4"])
    p300.dispense(90, plate_dilution["D1"])
    p300.mix(10, 20, plate_dilution["D1"])
    p300.drop_tip()
    # Well 2
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["D2"])
    p300.aspirate(30, plate_dilution["D1"])
    p300.dispense(30, plate_dilution["D2"])
    p300.mix(10, 20, plate_dilution["D2"])
    p300.drop_tip()
    # Well 3
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["D3"])
    p300.aspirate(30, plate_dilution["D2"])
    p300.dispense(30, plate_dilution["D3"])
    p300.mix(10, 20, plate_dilution["D3"])
    p300.drop_tip()
    # Well 4
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["D4"])
    p300.aspirate(30, plate_dilution["D3"])
    p300.dispense(30, plate_dilution["D4"])
    p300.mix(10, 20, plate_dilution["D4"])
    p300.drop_tip()
    # Well 5
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["D5"])
    p300.aspirate(30, plate_dilution["D4"])
    p300.dispense(30, plate_dilution["D5"])
    p300.mix(10, 20, plate_dilution["D5"])
    p300.drop_tip()
    # Well 6
    p300.pick_up_tip()
    p300.aspirate(60, reservoir["A1"])
    p300.dispense(60, plate_dilution["D6"])
    p300.aspirate(30, plate_dilution["D5"])
    p300.dispense(30, plate_dilution["D6"])
    p300.mix(10, 20, plate_dilution["D6"])
    p300.drop_tip()
    
    # Transfer 10 ul from each source well to assay plate and mix
    source_wells = [
        "A1","A2","A3","A4","A5","A6",
        "B1","B2","B3","B4","B5","B6",
        "C1","C2","C3","C4","C5","C6",
        "D1","D2","D3","D4","D5","D6"
    ]
    for src in source_wells:
        p20.pick_up_tip()
        p20.aspirate(10, plate_dilution[src])
        p20.dispense(10, plate_assay[src])
        p20.mix(5, 80, plate_assay[src])  # mix after dispense
        p20.drop_tip()
    
    # Home the robot
    protocol.home()
