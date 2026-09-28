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
    
    # Pick up a tip
    p300.pick_up_tip()
    
    # Get the first 48 destination wells
    dest_wells = list(block.wells())[:48]
    
    # Transfer in 8 cycles of 300 ul aspirate and 6 dispense steps
    for i in range(0, len(dest_wells), 6):
        p300.aspirate(300, source_tubes["A1"])
        # dispense 50 ul into each of the next 6 wells
        for j in range(6):
            p300.dispense(50, dest_wells[i + j])
    
    # Drop tip
    p300.drop_tip()
