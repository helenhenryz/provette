from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick 10ul from source wells to destination plate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "2")
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids for each source well
    protocol.define_liquid(name="liquid_B3", description="Source well B3", display_color="#FF0000")
    source_plate["B3"].load_liquid(liquid="liquid_B3", volume=100)

    protocol.define_liquid(name="liquid_C7", description="Source well C7", display_color="#00FF00")
    source_plate["C7"].load_liquid(liquid="liquid_C7", volume=100)

    protocol.define_liquid(name="liquid_D1", description="Source well D1", display_color="#0000FF")
    source_plate["D1"].load_liquid(liquid="liquid_D1", volume=100)

    protocol.define_liquid(name="liquid_A12", description="Source well A12", display_color="#FFFF00")
    source_plate["A12"].load_liquid(liquid="liquid_A12", volume=100)

    protocol.define_liquid(name="liquid_H6", description="Source well H6", display_color="#FF00FF")
    source_plate["H6"].load_liquid(liquid="liquid_H6", volume=100)

    protocol.define_liquid(name="liquid_E5", description="Source well E5", display_color="#00FFFF")
    source_plate["E5"].load_liquid(liquid="liquid_E5", volume=100)

    protocol.define_liquid(name="liquid_F9", description="Source well F9", display_color="#FFC000")
    source_plate["F9"].load_liquid(liquid="liquid_F9", volume=100)

    protocol.define_liquid(name="liquid_G2", description="Source well G2", display_color="#800000")
    source_plate["G2"].load_liquid(liquid="liquid_G2", volume=100)

    protocol.define_liquid(name="liquid_B11", description="Source well B11", display_color="#808000")
    source_plate["B11"].load_liquid(liquid="liquid_B11", volume=100)

    protocol.define_liquid(name="liquid_C4", description="Source well C4", display_color="#800080")
    source_plate["C4"].load_liquid(liquid="liquid_C4", volume=100)

    # Define source and destination well order
    source_wells = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]
    dest_wells = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1", "A2", "B2"]

    # Perform transfers
    for i, src in enumerate(source_wells):
        p20.pick_up_tip()
        p20.aspirate(10, source_plate[src])
        p20.dispense(10, dest_plate[dest_wells[i]])
        p20.drop_tip()
