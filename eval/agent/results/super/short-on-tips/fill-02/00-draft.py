import json
from opentrons import protocol_api

metadata = {"protocolName": "Aliquot protein 48x50ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load temperature module and PCR strip block
    temp_mod = protocol.load_module("temperature module gen2", 1)
    pcr_block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # load 15 mL tube rack
    tube_rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    # tip rack
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # define liquids
    protein = protocol.define_liquid(
        name="protein",
        description="protein stock",
        display_color="#FF0000"
    )
    # source tube A1 with 15000 ul protein
    tube_rack["A1"].load_liquid(liquid=protein, volume=15000)
    
    # pick up a single tip
    p300.pick_up_tip()
    # aspirate protein
    p300.aspirate(50, tube_rack["A1"])
    # dispense into 48 wells (columns 1-6, rows A-H)
    rows = ["A","B","C","D","E","F","G","H"]
    for col in range(1, 7):  # columns 1 to 6
        for row in rows:
            well = f"{row}{col}"
            p300.dispense(50, pcr_block[well])
    # drop tip
    p300.drop_tip()
