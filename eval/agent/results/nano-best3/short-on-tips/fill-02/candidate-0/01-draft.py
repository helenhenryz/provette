from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein into PCR strip tubes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tube rack with protein stock
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 1)
    # Define protein liquid
    protein_liquid = protocol.define_liquid(
        name="protein", description="protein stock", display_color="#FF0000"
    )
    # Load protein into well A1 of the tube rack with 5000 ul
    tubes["A1"].load_liquid(liquid=protein_liquid, volume=5000)
    # Load tip rack
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    # Load multi-channel pipette
    p300_multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tips])
    # Load temperature module and aluminium block
    module = protocol.load_module("temperature module gen2", 2)
    block = module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # Generate list of destination wells (first 48 wells of the block)
    dest_wells = []
    for row in ["A", "B", "C", "D", "E", "F"]:
        for col in range(1, 9):
            dest_wells.append(row + str(col))
    dest_wells = dest_wells[:48]
    # Pick up a tip
    p300_multi.pick_up_tip()
    # Transfer 50 ul to each of the 48 wells in groups of 8
    for i in range(0, 48, 8):
        # Aspirate 50 ul from the protein source
        p300_multi.aspirate(50, tubes["A1"])
        # Dispense 50 ul into 8 destination wells
        for well in dest_wells[i:i+8]:
            p300_multi.dispense(50, block[well])
    # Drop tip
    p300_multi.drop_tip()
