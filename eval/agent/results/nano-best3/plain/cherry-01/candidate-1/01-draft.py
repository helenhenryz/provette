from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick_10ul",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])

    # Define liquids for each source well
    source_B3_liquid = protocol.define_liquid(name="source_B3", description="Source well B3", display_color="#FF0000")
    source_C7_liquid = protocol.define_liquid(name="source_C7", description="Source well C7", display_color="#FF0101")
    source_D1_liquid = protocol.define_liquid(name="source_D1", description="Source well D1", display_color="#FF0202")
    source_A12_liquid = protocol.define_liquid(name="source_A12", description="Source well A12", display_color="#FF0303")
    source_H6_liquid = protocol.define_liquid(name="source_H6", description="Source well H6", display_color="#FF0404")
    source_E5_liquid = protocol.define_liquid(name="source_E5", description="Source well E5", display_color="#FF0505")
    source_F9_liquid = protocol.define_liquid(name="source_F9", description="Source well F9", display_color="#FF0606")
    source_G2_liquid = protocol.define_liquid(name="source_G2", description="Source well G2", display_color="#FF0707")
    source_B11_liquid = protocol.define_liquid(name="source_B11", description="Source well B11", display_color="#FF0808")
    source_C4_liquid = protocol.define_liquid(name="source_C4", description="Source well C4", display_color="#FF0909")

    # Load liquids into source wells with 100 ul each
    source_plate["B3"].load_liquid(liquid=source_B3_liquid, volume=100)
    source_plate["C7"].load_liquid(liquid=source_C7_liquid, volume=100)
    source_plate["D1"].load_liquid(liquid=source_D1_liquid, volume=100)
    source_plate["A12"].load_liquid(liquid=source_A12_liquid, volume=100)
    source_plate["H6"].load_liquid(liquid=source_H6_liquid, volume=100)
    source_plate["E5"].load_liquid(liquid=source_E5_liquid, volume=100)
    source_plate["F9"].load_liquid(liquid=source_F9_liquid, volume=100)
    source_plate["G2"].load_liquid(liquid=source_G2_liquid, volume=100)
    source_plate["B11"].load_liquid(liquid=source_B11_liquid, volume=100)
    source_plate["C4"].load_liquid(liquid=source_C4_liquid, volume=100)

    # Define the transfer pairs
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

    # Perform the transfers
    for src, dst in transfers:
        p20.pick_up_tip()
        p20.aspirate(10, source_plate[src])
        p20.dispense(10, dest_plate[dst])
        p20.drop_tip()
