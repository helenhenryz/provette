from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_48_templates",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    temp_module = protocol.load_module("temperature module gen2", 2)
    block = temp_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Define liquids
    # Template liquids
    # Generate first 48 well names from the strip (A1 to H12)
    template_well_names = [f"{col}{row}" for col in "ABCDEFGH" for row in range(1,13)][:48]
    for i, well_name in enumerate(template_well_names):
        well = block[well_name]
        well.load_liquid(
            liquid=protocol.define_liquid(
                name=f"template {i+1}",
                description=f"Template {i+1}",
                display_color=f"#{ (i+1):06X}"
            ),
            volume=10
        )
    
    # Define other components
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    block["E1"].load_liquid(liquid=fwd_primer, volume=150)
    
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#00FF01")
    block["E2"].load_liquid(liquid=rev_primer, volume=150)
    
    polymerase = protocol.define_liquid(name="polymerase", description="Polymerase", display_color="#0000FF")
    block["E3"].load_liquid(liquid=polymerase, volume=30)
    
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFFF00")
    block["E4"].load_liquid(liquid=dntp, volume=60)
    
    buffer = protocol.define_liquid(name="buffer", description="PCR buffer", display_color="#0000FF")
    reservoir["A1"].load_liquid(liquid=buffer, volume=1500)
    
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#00FFFF")
    reservoir["A2"].load_liquid(liquid=water, volume=2000)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Transfer components into each well
    for i, well_name in enumerate(plate.well_names()):
        p20.pick_up_tip()
        # 5 ul buffer
        p20.aspirate(5, reservoir["A1"])
        p20.dispense(5, plate[well_name])
        # 0.5 ul dNTP
        p20.aspirate(0.5, block["E4"])
        p20.dispense(0.5, plate[well_name])
        # 0.25 ul polymerase
        p20.aspirate(0.25, block["E3"])
        p20.dispense(0.25, plate[well_name])
        # 1.25 ul forward primer
        p20.aspirate(1.25, block["E1"])
        p20.dispense(1.25, plate[well_name])
        # 1.25 ul reverse primer
        p20.aspirate(1.25, block["E2"])
        p20.dispense(1.25, plate[well_name])
        # 14.75 ul water
        p20.aspirate(14.75, reservoir["A2"])
        p20.dispense(14.75, plate[well_name])
        # 2 ul template
        p20.aspirate(2, block[template_well_names[i]])
        p20.dispense(2, plate[well_name])
        p20.drop_tip()
