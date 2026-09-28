import json
from opentrons import protocol_api

metadata = {"protocolName": "Cherrypick", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 2)  # 2 mL deep wells
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # define liquids for each source well (any name)
    src_wells = ["B3", "C7", "D1", "A12", "H6", "E5", "F9", "G2", "B11", "C4"]
    for w in src_wells:
        liquid_name = f"src_{w}"
        liquid = protocol.define_liquid(name=liquid_name, description=f"Source {w}", display_color="#FF0000")
        source_plate[w].load_liquid(liquid=liquid, volume=500)  # within 2 mL capacity
    
    # cherrypick transfers, fresh tip each transfer to avoid cross-contamination
    transfers = [
        ("A1", "B3"),
        ("B1", "C7"),
        ("C1", "D1"),
        ("D1", "A12"),
        ("E1", "H6"),
        ("F1", "E5"),
        ("G1", "F9"),
        ("H1", "G2"),
        ("A2", "B11"),
        ("B2", "C4")
    ]
    for dest_well, src_well in transfers:
        p20.pick_up_tip()
        p20.transfer(10, source_plate[src_well], dest_plate[dest_well])
        p20.drop_tip()
