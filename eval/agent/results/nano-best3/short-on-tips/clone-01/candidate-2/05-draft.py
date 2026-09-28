from opentrons import protocol_api

metadata = {
    "protocolName": "Restriction Digests Setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module on slot 1
    temp_mod = protocol.load_module("temperature module gen2", 1)
    
    # Set temperature to 4°C
    temp_mod.set_temperature(4)
    
    # Load source plate (reagents) onto the temperature module
    source_plate = temp_mod.load_labware("nest_96_wellplate_200ul_flat")
    
    # Load destination plate (PCR plate) onto slot 2
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    
    # Load tip rack for p20 on slot 3
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    # Load p20 pipette on the right side
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x buffer", display_color="#0000FF")
    enzyme = protocol.define_liquid(name="enzyme", description="Restriction enzyme", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    plasmids = {}
    for i in range(1, 13):
        plasmids[f"plasmid {i}"] = protocol.define_liquid(name=f"plasmid {i}", description=f"Plasmid {i}", display_color=f"#{i:06X}")
    
    # Load liquids into source plate wells
    # Load plasmids (35 ul each) into wells A1-A12
    for i in range(1, 13):
        source_plate[f"A{i}"].load_liquid(liquid=plasmids[f"plasmid {i}"], volume=35)
    # Load buffer (35 ul) into well B1
    source_plate["B1"].load_liquid(liquid=buffer, volume=35)
    # Load enzyme (35 ul) into well B2
    source_plate["B2"].load_liquid(liquid=enzyme, volume=35)
    # Load water (194 ul) into well B3
    source_plate["B3"].load_liquid(liquid=water, volume=194)
    
    # Set up 12 restriction digests
    for i in range(1, 13):
        # Pick up a new tip
        p20.pick_up_tip()
        # Aspirate 2 ul buffer
        p20.aspirate(2, source_plate["B1"])
        # Aspirate 1 ul enzyme
        p20.aspirate(1, source_plate["B2"])
        # Aspirate 5 ul plasmid i
        p20.aspirate(5, source_plate[f"A{i}"])
        # Aspirate 12 ul water
        p20.aspirate(12, source_plate["B3"])
        # Dispense 20 ul into destination well A{i}
        p20.dispense(20, dest_plate[f"A{i}"])
        # Drop tip
        p20.drop_tip()
    
    # Deactivate temperature module
    temp_mod.deactivate()
