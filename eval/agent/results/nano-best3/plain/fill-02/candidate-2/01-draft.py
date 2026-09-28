from opentrons import protocol_api

metadata = {"protocolName": "Aliquot protein into 48 PCR strip tubes", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip rack
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    # Load source tube rack
    source_tube_rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    # Load temperature module and aluminium block
    temp_mod = protocol.load_module("temperature module gen2", 3)
    block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # Set temperature to keep protein stable
    temp_mod.set_temperature(4)
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    # Define protein liquid
    protein = protocol.define_liquid(name="protein", description="Protein stock", display_color="#FF0000")
    # Load protein into source well A1
    source_tube_rack["A1"].load_liquid(liquid=protein, volume=5000)
    # Generate list of target wells (first 48 wells: rows A-D, columns 1-12)
    target_wells = [f"{row}{col}" for row in "ABCD" for col in range(1,13)]
    # Transfer 50 ul to each target well
    for well in target_wells:
        p300.pick_up_tip()
        p300.aspirate(50, source_tube_rack["A1"])
        p300.dispense(50, block[well])
        p300.drop_tip()
    # Deactivate temperature module
    temp_mod.deactivate()
