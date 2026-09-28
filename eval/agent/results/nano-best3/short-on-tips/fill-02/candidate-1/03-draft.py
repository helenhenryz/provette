from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein stock into PCR strip tubes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define the protein liquid
    protein = protocol.define_liquid(
        name="protein",
        description="protein stock",
        display_color="#800080"
    )
    
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    temperature_module = protocol.load_module("temperature module gen2", 3)
    aluminum_block = temperature_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Load the protein liquid into the source well
    tubes["A1"].load_liquid(liquid=protein, volume=3000)
    
    # Set up pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Pick up a tip once
    p300.pick_up_tip()
    
    # Aliquot 50 ul into 48 wells (first 4 rows)
    for row in aluminum_block.rows()[:4]:
        for well in row:
            p300.aspirate(50, tubes["A1"])
            p300.dispense(50, well)
    
    # Drop the tip
    p300.drop_tip()
