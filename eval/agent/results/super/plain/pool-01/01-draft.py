import json
from opentrons import protocol_api

metadata = {"protocolName": "Pool 48 libraries", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    
    # define liquids
    lib_names = [f"library {i}" for i in range(1, 49)]
    liquids = {}
    for name in lib_names:
        liquids[name] = protocol.define_liquid(
            name=name,
            description="indexed sequencing library",
            display_color="#FF6600"
        )
    
    # load liquids into plate wells A1-H6 (48 wells)
    well_list = plate.wells()[:48]  # first 48 wells
    for i, well in enumerate(well_list):
        well.load_liquid(liquid=liquids[lib_names[i]], volume=20)  # starting volume 20 µL
    
    # destination tube
    dest_well = tuberack["A1"]
    # no need to load liquid initially; empty
    
    # transfer 5 µL from each library well to destination tube
    for src_well in well_list:
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest_well)
        p20.drop_tip()
