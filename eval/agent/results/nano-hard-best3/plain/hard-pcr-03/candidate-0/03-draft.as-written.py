from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_48_reactions",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip_rack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    # Load aluminum block onto the temperature module (cold block)
    component_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    template_tuberack_1 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 6)
    template_tuberack_2 = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 7)
    
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack_300])
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x buffer", display_color="#0000FF")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#00FF00")
    polymerase = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#FF0000")
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FFFF")
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#FFFF00")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#000000")
    
    # Define template liquids 1-48
    templates = {}
    for i in range(1, 49):
        templates[f"template {i}"] = protocol.define_liquid(name=f"template {i}", description=None)
    
    # Load component liquids into component_block
    component_block["A1"].load_liquid(liquid=buffer, volume=300)
    component_block["A2"].load_liquid(liquid=dntp, volume=30)
    component_block["A3"].load_liquid(liquid=polymerase, volume=20)
    component_block["A4"].load_liquid(liquid=fwd_primer, volume=100)
    component_block["A5"].load_liquid(liquid=rev_primer, volume=100)
    component_block["A6"].load_liquid(liquid=water, volume=1000)
    
    # Load template liquids into template racks
    rack_well_names = []
    for row in "ABCD":
        for col in range(1, 7):
            rack_well_names.append(f"{row}{col}")
    for i, well_name in enumerate(rack_well_names):
        well = template_tuberack_1[well_name]
        well.load_liquid(liquid=templates[f"template {i+1}"], volume=10)
    for i, well_name in enumerate(rack_well_names):
        well = template_tuberack_2[well_name]
        well.load_liquid(liquid=templates[f"template {i+25}"], volume=10)
    
    # Prepare master mix in reservoir["A1"]
    p300.pick_up_tip()
    p300.aspirate(240, component_block["A1"])
    p300.dispense(240, reservoir["A1"])
    p300.aspirate(24, component_block["A2"])
    p300.dispense(24, reservoir["A1"])
    p300.aspirate(12, component_block["A3"])
    p300.dispense(12, reservoir["A1"])
    p300.aspirate(60, component_block["A4"])
    p300.dispense(60, reservoir["A1"])
    p300.aspirate(60, component_block["A4"])
    p300.dispense(60, reservoir["A1"])
    p300.aspirate(60, component_block["A5"])
    p300.dispense(60, reservoir["A1"])
    p300.aspirate(300, component_block["A6"])
    p300.dispense(300, reservoir["A1"])
    p300.aspirate(300, component_block["A6"])
    p300.dispense(300, reservoir["A1"])
    p300.aspirate(108, component_block["A6"])
    p300.dispense(108, reservoir["A1"])
    p300.drop_tip()
    
    # Get list of reaction wells (first 48 wells of plate)
    reaction_wells = []
    for row in range(4):  # rows 0-3 (A-D)
        for col in range(12):  # columns 0-11 (1-12)
            well_name = f"{chr(65+row)}{col+1}"
            reaction_wells.append(plate[well_name])
    
    # Get list of template wells (48 wells across two racks)
    rack_well_names = []
    for row in "ABCD":
        for col in range(1, 7):
            rack_well_names.append(f"{row}{col}")
    template_wells_1 = [template_tuberack_1[well] for well in rack_well_names]
    template_wells_2 = [template_tuberack_2[well] for well in rack_well_names]
    template_wells = template_wells_1 + template_wells_2
    
    # Transfer master mix (23 ul) to each reaction well
    p300.pick_up_tip()
    for reaction_well in reaction_wells:
        p300.aspirate(23, reservoir["A1"])
        p300.dispense(23, reaction_well)
    p300.drop_tip()
    
    # Add 2 ul of template to each reaction well
    p20.pick_up_tip()
    for reaction_well, template_well in zip(reaction_wells, template_wells):
        p20.aspirate(2, template_well)
        p20.dispense(2, reaction_well)
    p20.drop_tip()
