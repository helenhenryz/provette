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
    for i in range(1, 49):
        block["A"+str(i)].load_liquid(
            liquid=protocol.define_liquid(
                name=f"template {i}",
                description=f"Template {i}",
                display_color=f"#{i:06X}"
            ),
            volume=10
        )
    
    # Define and load fwd primer
    fwd_primer = protocol.define_liquid(name="fwd primer", description="Forward primer", display_color="#00FF00")
    block["A49"].load_liquid(liquid=fwd_primer, volume=150)
    
    # Define and load rev primer
    rev_primer = protocol.define_liquid(name="rev primer", description="Reverse primer", display_color="#00FF01")
    block["A50"].load_liquid(liquid=rev_primer, volume=150)
    
    # Define and load polymerase
    polymerase = protocol.define_liquid(name="polymerase", description="Polymerase", display_color="#0000FF")
    block["A51"].load_liquid(liquid=polymerase, volume=30)
    
    # Define and load dntp
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFFF00")
    block["A52"].load_liquid(liquid=dntp, volume=60)
    
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
    p20.aspirate(50, block["A52"])
    p20.dispense(50, reservoir["A3"])
    p20.aspirate(25, block["A51"])
    p20.dispense(25, reservoir["A3"])
    p20.aspirate(125, block["A49"])
    p20.dispense(125, reservoir["A3"])
    p20.aspirate(125, block["A50"])
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
        p20.aspirate(2, block["A"+str(i+1)])
        # Dispense into plate well
        plate[well_name].dispense(2, plate[well_name])
        p20.drop_tip()
