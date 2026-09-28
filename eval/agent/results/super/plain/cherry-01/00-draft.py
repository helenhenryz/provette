import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Cherrypick 10 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])
    
    # define liquids for each source well
    source_wells = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]
    for well in source_wells:
        liq_name = f"Sample_{well}"
        protocol.define_liquid(
            name=liq_name,
            description=f"Sample from {well}",
            display_color="#FF0000"
        )
        source_plate[well].load_liquid(liq_name, volume=200)  # arbitrary starting volume
    
    # destination wells consecutive starting A1 down column
    dest_wells = ["A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1", "A2", "B2"]
    
    for src, dst in zip(source_wells, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(10, source_plate[src])
        p20.dispense(10, dest_plate[dst])
        p20.drop_tip()
    
