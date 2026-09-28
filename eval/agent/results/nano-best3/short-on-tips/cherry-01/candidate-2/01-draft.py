from opentrons import protocol_api

metadata = {"protocolName": "Cherrypick_10ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids for each source well
    src_B3 = protocol.define_liquid(name="source_B3", description="source from B3", display_color="#000000")
    source_plate["B3"].load_liquid(liquid=src_B3, volume=100)

    src_C7 = protocol.define_liquid(name="source_C7", description="source from C7", display_color="#000000")
    source_plate["C7"].load_liquid(liquid=src_C7, volume=100)

    src_D1 = protocol.define_liquid(name="source_D1", description="source from D1", display_color="#000000")
    source_plate["D1"].load_liquid(liquid=src_D1, volume=100)

    src_A12 = protocol.define_liquid(name="source_A12", description="source from A12", display_color="#000000")
    source_plate["A12"].load_liquid(liquid=src_A12, volume=100)

    src_H6 = protocol.define_liquid(name="source_H6", description="source from H6", display_color="#000000")
    source_plate["H6"].load_liquid(liquid=src_H6, volume=100)

    src_E5 = protocol.define_liquid(name="source_E5", description="source from E5", display_color="#000000")
    source_plate["E5"].load_liquid(liquid=src_E5, volume=100)

    src_F9 = protocol.define_liquid(name="source_F9", description="source from F9", display_color="#000000")
    source_plate["F9"].load_liquid(liquid=src_F9, volume=100)

    src_G2 = protocol.define_liquid(name="source_G2", description="source from G2", display_color="#000000")
    source_plate["G2"].load_liquid(liquid=src_G2, volume=100)

    src_B11 = protocol.define_liquid(name="source_B11", description="source from B11", display_color="#000000")
    source_plate["B11"].load_liquid(liquid=src_B11, volume=100)

    src_C4 = protocol.define_liquid(name="source_C4", description="source from C4", display_color="#000000")
    source_plate["C4"].load_liquid(liquid=src_C4, volume=100)

    # Define the transfer pairs in order
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
