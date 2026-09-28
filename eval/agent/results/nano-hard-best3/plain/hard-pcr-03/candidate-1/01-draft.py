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
    # Define template liquids
    template_wells = block.well_names()[:48]  # Get the first 48 well names
    for i, well_name in enumerate(template_wells):
        well = block[well_name]
        well.load_liquid(
            liquid=protocol.define_liquid(
                name=f"template {i+1}",
                description=f"Template {i+1}",
                display_color=f"#{ (i+1):06X}"
            ),
            volume=10
        )
    
    # Define and load fwd primer
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    block["E1"].load_liquid(liquid=fwd_primer, volume=150)
    
    # Define and load rev primer
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#00FF01")
    block["E2"].load_liquid(liquid=rev_primer, volume=150)
    
    # Define and load polymerase
    polymerase = protocol.define_liquid(name="polymerase", description="Polymerase", display_color="#0000FF")
    block["E3"].load_liquid(liquid=polymerase, volume=30)
    
    # Define and load dntp
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFFF00")
    block["E4"].load_liquid(liquid=dntp, volume=60)
    
    # Define and load buffer
    buffer = protocol.define_liquid(name="buffer", description="PCR buffer", display_color="#0000FF")
    reservoir["A1"].load_liquid(liquid=buffer, volume=1500)
    
    # Define and load water
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#00FFFF")
    reservoir["A2"].load_liquid(liquid=water, volume=2000)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Create master mix in reservoir["A3"]
    p20.pick_up_tip()
    p20.aspirate(500, reservoir["A1"])
    p20.dispense(500, reservoir["A3"])
    p20.aspirate(50, block["E4"])
    p20.dispense(50, reservoir["A3"])
    p20.aspirate(25, block["E3"])
    p20.dispense(25, reservoir["A3"])
    p20.aspirate(125, block["E1"])
    p20.dispense(125, reservoir["A3"])
    p20.aspirate(125, block["E2"])
    p20.dispense(125, reservoir["A3"])
    p20.aspirate(1475, reservoir["A2"])
    p20.dispense(1475, reservoir["A3"])
    # Mix master mix
    for _ in range(3):
        p20.aspirate(10, reservoir["A3"])
        p20.dispense(10, reservoir["A3"])
    p20.drop_tip()
    
    # Assemble reactions
    for i in range(48):
        well_name = plate.well_names()[i]
        p20.pick_up_tip()
        # Aspirate 23 ul master mix
        p20.aspirate(23, reservoir["A3"])
        # Dispense into plate well
        plate[well_name].dispense(23, plate[well_name])
        # Aspirate 2 ul template
        p20.aspirate(2, block[template_wells[i]])
        # Dispense into plate well
        plate[well_name].dispense(2, plate[well_name])
        p20.drop_tip()
