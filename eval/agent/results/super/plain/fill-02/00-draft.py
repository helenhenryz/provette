import json
from opentrons import protocol_api

metadata = {"protocolName": "Aliquot protein", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    temp_mod = protocol.load_module("temperature module gen2", "1")
    block = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    tuberack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", "2")
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "3")
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # liquids
    protein = protocol.define_liquid(
        name="protein",
        description="Protein stock",
        display_color="#FF0000"
    )
    # source well A1 of 15ml tube
    tuberack["A1"].load_liquid(liquid=protein, volume=15000)  # ul
    
    # destinations: first 48 wells of block (A1..H6)
    dest_wells = [block[well] for well in 
                  ['A1','B1','C1','D1','E1','F1','G1','H1',
                   'A2','B2','C2','D2','E2','F2','G2','H2',
                   'A3','B3','C3','D3','E3','F3','G3','H3',
                   'A4','B4','C4','D4','E4','F4','G4','H4',
                   'A5','B5','C5','D5','E5','F5','G5','H5',
                   'A6','B6','C6','D6','E6','F6','G6','H6']]
    
    for well in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(50, tuberack["A1"])
        p300.dispense(50, well)
        p300.drop_tip()
