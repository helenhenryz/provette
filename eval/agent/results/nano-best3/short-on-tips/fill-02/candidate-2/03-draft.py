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
    
    # Set temperature for the block to 4°C
    temp_module.set_temperature(4)
    
    # Pick up a tip
    p300.pick_up_tip()
    
    # Aspirate total volume needed (48 * 50 = 2400 ul)
    p300.aspirate(2400, source_tubes["A1"])
    
    # Transfer 50 ul into each of the first 48 wells of the block
    dest_wells = list(block.wells())[:48]
    for well in dest_wells:
        p300.dispense(50, well)
    
    # Drop tip
    p300.drop_tip()
    
    # Deactivate temperature module
    temp_module.deactivate()
