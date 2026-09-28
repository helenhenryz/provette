from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein stock into PCR strip tubes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define the protein liquid
    protein = protocol.define_liquid(
        name="protein",
        volume=3000,
        description="protein stock",
        display_color="#800080"
    )
    
    # Load labware
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 1)
    tip_rack = protocol.load_labware("opentrons_96_filtertiprack_200ul", 2)
    temperature_module = protocol.load_module("temperature module gen2", 3)
    aluminum_block = temperature_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Load the protein liquid into the source well
    tubes["A1"].load_liquid(liquid=protein, volume=3000)
    
    # Set up pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Pick up a tip once
    p300.pick_up_tip()
    
    # Aliquot 50 ul into 48 wells
    for well_name in aluminum_block.wells()[:48]:
        p300.aspirate(50, tubes["A1"])
        p300.dispense(50, aluminum_block[well_name])
    
    # Drop the tip
    p300.drop_tip()
