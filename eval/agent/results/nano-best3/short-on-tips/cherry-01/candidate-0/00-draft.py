from opentrons import protocol_api

metadata = {"protocolName": "Cherrypick_10ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Define liquids (one per source well)
    protocol.define_liquid(name="B3", description="Sample from well B3", display_color="#FF0000")
    protocol.define_liquid(name="C7", description="Sample from well C7", display_color="#00FF00")
    protocol.define_liquid(name="D1", description="Sample from well D1", display_color="#0000FF")
    protocol.define_liquid(name="A12", description="Sample from well A12", display_color="#FFFF00")
    protocol.define_liquid(name="H6", description="Sample from well H6", display_color="#FF00FF")
    protocol.define_liquid(name="E5", description="Sample from well E5", display_color="#00FFFF")
    protocol.define_liquid(name="F9", description="Sample from well F9", display_color="#FF007F")
    protocol.define_liquid(name="G2", description="Sample from well G2", display_color="#7F00FF")
    protocol.define_liquid(name="B11", description="Sample from well B11", display_color="#007F00")
    protocol.define_liquid(name="C4", description="Sample from well C4", display_color="#7F0000")
    
    # Load each liquid into its source well (100 ul each)
    source_plate["B3"].load_liquid(liquid="B3", volume=100)
    source_plate["C7"].load_liquid(liquid="C7", volume=100)
    source_plate["D1"].load_liquid(liquid="D1", volume=100)
    source_plate["A12"].load_liquid(liquid="A12", volume=100)
    source_plate["H6"].load_liquid(liquid="H6", volume=100)
    source_plate["E5"].load_liquid(liquid="E5", volume=100)
    source_plate["F9"].load_liquid(liquid="F9", volume=100)
    source_plate["G2"].load_liquid(liquid="G2", volume=100)
    source_plate["B11"].load_liquid(liquid="B11", volume=100)
    source_plate["C4"].load_liquid(liquid="C4", volume=100)
    
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
