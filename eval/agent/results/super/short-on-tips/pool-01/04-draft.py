import json
from opentrons import protocol_api

metadata = {"protocolName": "Pool 48 libraries", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    dest_tube = tuberack["A1"]  # destination for pooled libraries
    
    # define liquids
    lib_names = [f"library {i}" for i in range(1, 49)]
    liquids = {}
    for i, name in enumerate(lib_names, start=1):
        liq = protocol.define_liquid(name=name, description=f"Library {i}", display_color="#FF0000")
        liquids[name] = liq
        # place each library in plate wells A1..D12 (first 48 wells)
        well = plate.wells()[i-1]  # zero-indexed
        well.load_liquid(liq, volume=50)  # starting volume 50 µL to keep tip submerged
    
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack300])
    
    # transfer 5 µL from each library well to destination tube
    for src_well, lib_name in zip(plate.wells()[:48], lib_names):
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest_tube)
        p20.drop_tip()
    
    # mix the pooled tube to ensure homogeneity using p300
    p300.pick_up_tip()
    p300.mix(5, 192, dest_tube)  # 5 repetitions, 192 µL each = ~960 µL moved (covers volume)
    p300.drop_tip()
