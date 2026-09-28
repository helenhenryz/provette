from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick 10 ul",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids (source wells)
    liquid_B3 = protocol.define_liquid(name="B3", description="Source well B3", display_color="#FF0000")
    liquid_C7 = protocol.define_liquid(name="C7", description="Source well C7", display_color="#00FF00")
    liquid_D1 = protocol.define_liquid(name="D1", description="Source well D1", display_color="#0000FF")
    liquid_A12 = protocol.define_liquid(name="A12", description="Source well A12", display_color="#FFFF00")
    liquid_H6 = protocol.define_liquid(name="H6", description="Source well H6", display_color="#FF00FF")
    liquid_E5 = protocol.define_liquid(name="E5", description="Source well E5", display_color="#00FFFF")
    liquid_F9 = protocol.define_liquid(name="F9", description="Source well F9", display_color="#FF0000")
    liquid_G2 = protocol.define_liquid(name="G2", description="Source well G2", display_color="#808080")
    liquid_B11 = protocol.define_liquid(name="B11", description="Source well B11", display_color="#800000")
    liquid_C4 = protocol.define_liquid(name="C4", description="Source well C4", display_color="#008000")
    
    # Load liquids into source wells
    source_plate["B3"].load_liquid(liquid=liquid_B3, volume=100)
    source_plate["C7"].load_liquid(liquid=liquid_C7, volume=100)
    source_plate["D1"].load_liquid(liquid=liquid_D1, volume=100)
    source_plate["A12"].load_liquid(liquid=liquid_A12, volume=100)
    source_plate["H6"].load_liquid(liquid=liquid_H6, volume=100)
    source_plate["E5"].load_liquid(liquid=liquid_E5, volume=100)
    source_plate["F9"].load_liquid(liquid=liquid_F9, volume=100)
    source_plate["G2"].load_liquid(liquid=liquid_G2, volume=100)
    source_plate["B11"].load_liquid(liquid=liquid_B11, volume=100)
    source_plate["C4"].load_liquid(liquid=liquid_C4, volume=100)
    
    # Cherrypick transfers
    # Transfer 1: B3 -> A1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["B3"])
    p20.dispense(10, dest_plate["A1"])
    p20.drop_tip()
    # Transfer 2: C7 -> B1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["C7"])
    p20.dispense(10, dest_plate["B1"])
    p20.drop_tip()
    # Transfer 3: D1 -> C1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["D1"])
    p20.dispense(10, dest_plate["C1"])
    p20.drop_tip()
    # Transfer 4: A12 -> D1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["A12"])
    p20.dispense(10, dest_plate["D1"])
    p20.drop_tip()
    # Transfer 5: H6 -> E1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["H6"])
    p20.dispense(10, dest_plate["E1"])
    p20.drop_tip()
    # Transfer 6: E5 -> F1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["E5"])
    p20.dispense(10, dest_plate["F1"])
    p20.drop_tip()
    # Transfer 7: F9 -> G1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["F9"])
    p20.dispense(10, dest_plate["G1"])
    p20.drop_tip()
    # Transfer 8: G2 -> H1
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["G2"])
    p20.dispense(10, dest_plate["H1"])
    p20.drop_tip()
    # Transfer 9: B11 -> A2
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["B11"])
    p20.dispense(10, dest_plate["A2"])
    p20.drop_tip()
    # Transfer 10: C4 -> B2
    p20.pick_up_tip()
    p20.aspirate(10, source_plate["C4"])
    p20.dispense(10, dest_plate["B2"])
    p20.drop_tip()
