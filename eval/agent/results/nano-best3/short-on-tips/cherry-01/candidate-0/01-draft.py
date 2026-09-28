from opentrons import protocol_api

metadata = {"protocolName": "Cherrypick_10ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Define liquids (one per source well) and load them
    b3_liquid = protocol.define_liquid(name="B3", description="Sample from well B3", display_color="#FF0000")
    source_plate["B3"].load_liquid(liquid=b3_liquid, volume=100)
    
    c7_liquid = protocol.define_liquid(name="C7", description="Sample from well C7", display_color="#00FF00")
    source_plate["C7"].load_liquid(liquid=c7_liquid, volume=100)
    
    d1_liquid = protocol.define_liquid(name="D1", description="Sample from well D1", display_color="#0000FF")
    source_plate["D1"].load_liquid(liquid=d1_liquid, volume=100)
    
    a12_liquid = protocol.define_liquid(name="A12", description="Sample from well A12", display_color="#FFFF00")
    source_plate["A12"].load_liquid(liquid=a12_liquid, volume=100)
    
    h6_liquid = protocol.define_liquid(name="H6", description="Sample from well H6", display_color="#FF00FF")
    source_plate["H6"].load_liquid(liquid=h6_liquid, volume=100)
    
    e5_liquid = protocol.define_liquid(name="E5", description="Sample from well E5", display_color="#00FFFF")
    source_plate["E5"].load_liquid(liquid=e5_liquid, volume=100)
    
    f9_liquid = protocol.define_liquid(name="F9", description="Sample from well F9", display_color="#FF007F")
    source_plate["F9"].load_liquid(liquid=f9_liquid, volume=100)
    
    g2_liquid = protocol.define_liquid(name="G2", description="Sample from well G2", display_color="#7F00FF")
    source_plate["G2"].load_liquid(liquid=g2_liquid, volume=100)
    
    b11_liquid = protocol.define_liquid(name="B11", description="Sample from well B11", display_color="#007F00")
    source_plate["B11"].load_liquid(liquid=b11_liquid, volume=100)
    
    c4_liquid = protocol.define_liquid(name="C4", description="Sample from well C4", display_color="#7F0000")
    source_plate["C4"].load_liquid(liquid=c4_liquid, volume=100)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define the source-destination pairs in order
    transfers = [
        ("B3", "A1"),
        ("C7", "B1"),
        ("D1", "C1"),
        ("A12", "D1"),
        ("H6", "E1"),
        ("E5", "F1"),
        ("F9", "G1"),
        ("G2", "H1"),
        ("B11", "A2"),
        ("C4", "B2")
    ]
    
    # Perform transfers
    p20.pick_up_tip()
    for src, dest in transfers:
        p20.aspirate(10, source_plate[src])
        p20.dispense(10, dest_plate[dest])
    p20.drop_tip()
