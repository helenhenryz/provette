import json
from opentrons import protocol_api

metadata = {"protocolName": "PCR Setup 8x100ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # define liquids
    mix = protocol.define_liquid(name="mix", description="2x master mix", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#00FF00")
    templates = []
    for i in range(1, 9):
        t = protocol.define_liquid(name=f"template {i}", description=f"template {i}", display_color="#0000FF")
        templates.append(t)
    
    # load labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    
    # load liquids into source wells
    # mix in A1, water in A2, templates in B1,B2,B3,B4,C1,C2,C3,C4
    tuberack["A1"].load_liquid(liquid=mix, volume=500)   # excess
    tuberack["A2"].load_liquid(liquid=water, volume=400)
    template_wells = ["B1","B2","B3","B4","C1","C2","C3","C4"]
    for well_name, t in zip(template_wells, templates):
        tuberack[well_name].load_liquid(liquid=t, volume=20)   # 8 ul needed + excess
    
    # pipettes
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tiprack])
    p300_single = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])
    
    # dispense mix (50 ul) to column 1 wells A1-H1
    p300_multi.pick_up_tip()
    mix_well = tuberack["A1"]
    dest_wells = [plate[f"{chr(65+r)}1"] for r in range(8)]  # A1-H1
    for dw in dest_wells:
        p300_multi.aspirate(50, mix_well)
        p300_multi.dispense(50, dw)
        p300_multi.blow_out(dw)
    p300_multi.drop_tip()
    
    # dispense water (42 ul) to same wells
    p300_multi.pick_up_tip()
    water_well = tuberack["A2"]
    for dw in dest_wells:
        p300_multi.aspirate(42, water_well)
        p300_multi.dispense(42, dw)
        p300_multi.blow_out(dw)
    p300_multi.drop_tip()
    
    # add templates (8 ul each) using single channel
    for well_name, dst in zip(template_wells, dest_wells):
        src = tuberack[well_name]
        p300_single.pick_up_tip()
        p300_single.aspirate(8, src)
        p300_single.dispense(8, dst)
        p300_single.blow_out(dst)
        p300_single.drop_tip()
