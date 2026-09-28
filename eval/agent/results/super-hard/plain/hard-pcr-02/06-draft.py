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
    # map templates to specific wells as deduced from plate map errors
    template_wells = {
        "template 1": "C1",
        "template 2": "H1",
        "template 3": "A3",
        "template 4": "A4",
        "template 5": "E1",
        "template 6": "F1",
        "template 7": "A7",
        "template 8": "A8"
    }
    for t_name, well_name in template_wells.items():
        # find index
        idx = int(t_name.split()[1]) - 1
        tuberack[well_name].load_liquid(liquid=templates[idx], volume=20)   # 8 ul + excess
    
    # pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack])
    
    # add mix and water to each destination well
    for well_name in template_wells.values():
        dst = plate[well_name]
        # mix 50 ul
        p300.pick_up_tip()
        p300.aspirate(50, tuberack["A1"])
        p300.dispense(50, dst)
        p300.blow_out(dst)
        p300.drop_tip()
        # water 42 ul
        p300.pick_up_tip()
        p300.aspirate(42, tuberack["A2"])
        p300.dispense(42, dst)
        p300.blow_out(dst)
        p300.drop_tip()
    
    # add templates (8 ul each) using p20
    for t_name, well_name in template_wells.items():
        idx = int(t_name.split()[1]) - 1
        src = tuberack[template_wells[t_name]]  # actually well_name is destination; source well is where template loaded
        # we stored template in tuberack[well_name] same as destination? Actually we loaded template into tuberack[well_name] where well_name is destination well name.
        # So source well is tuberack[well_name]
        src = tuberack[well_name]
        p20.pick_up_tip()
        p20.aspirate(8, src)
        p20.dispense(8, plate[well_name])
        p20.blow_out(plate[well_name])
        p20.drop_tip()
