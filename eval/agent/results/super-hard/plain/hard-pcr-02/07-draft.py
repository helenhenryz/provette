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
    tuberack["A1"].load_liquid(liquid=mix, volume=500)   # excess
    tuberack["A2"].load_liquid(liquid=water, volume=400)
    # source wells for templates in tuberack
    template_source_wells = ["A3","A4","A5","A6","B1","B2","B3","B4"]
    for well_name, t in zip(template_source_wells, templates):
        tuberack[well_name].load_liquid(liquid=t, volume=20)   # 8 ul + excess
    
    # destination map per template number (1-indexed)
    dest_map = {
        1: "C1",
        2: "H1",
        3: "A3",
        4: "A4",
        5: "E1",
        6: "F1",
        7: "A7",
        8: "A8"
    }
    
    # pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])
    
    # collect all destination wells
    dest_wells = [plate[dest_map[i]] for i in range(1, 9)]
    
    # add mix (50 ul) to each destination well
    for dw in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(50, tuberack["A1"])
        p300.dispense(50, dw)
        p300.blow_out(dw)
        p300.drop_tip()
    
    # add water (42 ul) to each destination well
    for dw in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(42, tuberack["A2"])
        p300.dispense(42, dw)
        p300.blow_out(dw)
        p300.drop_tip()
    
    # add templates (8 ul each) using p20
    for i in range(1, 9):
        src_well = tuberack[template_source_wells[i-1]]
        dst_well = plate[dest_map[i]]
        p20.pick_up_tip()
        p20.aspirate(8, src_well)
        p20.dispense(8, dst_well)
        p20.blow_out(dst_well)
        p20.drop_tip()
