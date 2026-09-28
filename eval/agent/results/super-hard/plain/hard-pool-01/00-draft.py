import json
from opentrons import protocol_api

metadata = {"protocolName": "Pool 96 libraries", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tube_rack = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 3)
    destination_tube = tube_rack["A1"]
    
    # Define liquids
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
              "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    for i in range(1, 97):
        lib_name = f"library {i}"
        color = colors[(i-1) % len(colors)]
        protocol.define_liquid(name=lib_name, description=f"Indexed library {i}", display_color=color)
        well = source_plate[f"{chr(ord('A') + (i-1)//12)}{((i-1) % 12) + 1}"]
        well.load_liquid(liquid=protocol.get_liquid_by_name(lib_name), volume=100)  # starting vol
    
    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    p300.pick_up_tip()
    for i in range(1, 97):
        well = source_plate[f"{chr(ord('A') + (i-1)//12)}{((i-1) % 12) + 1}"]
        p300.aspirate(25, well)
        p300.dispense(25, destination_tube)
        p300.blow_out(destination_tube)
    p300.drop_tip()
