from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_48_reactions",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip rack and instrument
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])
    
    # Load destination plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    
    # Load temperature modules and racks
    components_module = protocol.load_module("temperature module gen2", 2)
    components_rack = components_module.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    templates_module1 = protocol.load_module("temperature module gen2", 4)
    templates_rack1 = templates_module1.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    templates_module2 = protocol.load_module("temperature module gen2", 5)
    templates_rack2 = templates_module2.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    
    # Load reservoir for master mix
    master_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 6)
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x buffer", display_color="#0000FF")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#00FF00")
    polymerase = protocol.define_liquid(name="polymerase", description="Taq polymerase", display_color="#FF0000")
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FFFF")
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#FFFF00")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    
    # Define template liquids
    for i in range(1, 49):
        tmpl_liquid = protocol.define_liquid(name=f"template {i}", description=f"Template {i}", display_color="#808080")
        if i < 25:
            templates_rack1[f"A{i}"].load_liquid(liquid=tmpl_liquid, volume=10)
        else:
            templates_rack2["A{}".format(i-24)].load_liquid(liquid=tmpl_liquid, volume=10)
    
    # Load liquids into source wells
    components_rack["A1"].load_liquid(liquid=buffer, volume=500)
    components_rack["A2"].load_liquid(liquid=dntp, volume=100)
    components_rack["A3"].load_liquid(liquid=polymerase, volume=20)
    components_rack["A4"].load_liquid(liquid=fwd_primer, volume=200)
    components_rack["A5"].load_liquid(liquid=rev_primer, volume=200)
    components_rack["A6"].load_liquid(liquid=water, volume=1000)
    
    # Prepare master mix in reservoir
    p300.pick_up_tip()
    
    # Add buffer
    p300.aspirate(240, components_rack["A1"])
    p300.dispense(240, master_reservoir["A1"])
    
    # Add dNTPs
    p300.aspirate(24, components_rack["A2"])
    p300.dispense(24, master_reservoir["A1"])
    
    # Add polymerase
    p300.aspirate(12, components_rack["A3"])
    p300.dispense(12, master_reservoir["A1"])
    
    # Add fwd primer
    p300.aspirate(60, components_rack["A4"])
    p300.dispense(60, master_reservoir["A1"])
    
    # Add rev primer
    p300.aspirate(60, components_rack["A5"])
    p300.dispense(60, master_reservoir["A1"])
    
    # Add water
    p300.aspirate(708, components_rack["A6"])
    p300.dispense(708, master_reservoir["A1"])
    
    # Generate list of destination wells (first 48 wells of the plate)
    dest_well_names = []
    for row in "ABCD":
        for col in range(1, 13):
            dest_well_names.append(row + str(col))
    
    # Process each of the 48 reactions
    for i, well_name in enumerate(dest_well_names):
        dest_well = plate[well_name]
        # Aspirate 23 ul of master mix
        p300.aspirate(23, master_reservoir["A1"])
        # Dispense into destination well
        p300.dispense(23, dest_well)
        # Determine template source well
        if i < 24:
            tmpl_well_name = f"A{i+1}"
            tmpl_source = templates_rack1[tmpl_well_name]
        else:
            tmpl_well_name = f"A{i-23}"
            tmpl_source = templates_rack2[tmpl_well_name]
        # Aspirate 2 ul of template
        p300.aspirate(2, tmpl_source)
        # Dispense into destination well
        p300.dispense(2, dest_well)
    
    # Drop tip
    p300.drop_tip()
