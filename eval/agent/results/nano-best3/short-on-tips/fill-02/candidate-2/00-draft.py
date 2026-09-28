from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein into PCR strip tubes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    temp_module = protocol.load_module("temperature module gen2", 3)
    block = temp_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Define liquids
    protein = protocol.define_liquid(name="protein", description="Protein stock", display_color="#FF0000")
    source_tubes["A1"].load_liquid(liquid=protein, volume=15000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])
    
    # Aspirate 2400 ul from source
    p300.aspirate(2400, source_tubes["A1"])
    
    # Dispense 50 ul into each of the first 48 wells of the block
    dest_wells = block.wells()
    for i, well in enumerate(dest_wells):
        if i < 48:
            p300.dispense(50, well)
    
    # Drop tip
    p300.drop_tip()
