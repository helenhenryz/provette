from opentrons import protocol_api

metadata = {
    "protocolName": "Ligation_24_reactions",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x T4 DNA ligase buffer", display_color="#0000FF")
    ligase = protocol.define_liquid(name="ligase", description="T4 DNA Ligase", display_color="#00FF00")
    vector = protocol.define_liquid(name="vector", description="Cut Vector", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#000000")
    inserts = {}
    for i in range(1, 25):
        inserts[i] = protocol.define_liquid(name=f"insert {i}", description=f"Insert {i}", display_color="#FFFFFF")
    
    # Load modules and labware
    temperature_module = protocol.load_module("temperature module gen2", 1)
    block = temperature_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    inserts_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)
    
    # Load liquids into source wells
    block["A1"].load_liquid(liquid=buffer, volume=100)
    block["A2"].load_liquid(liquid=ligase, volume=100)
    block["A3"].load_liquid(liquid=vector, volume=100)
    block["A4"].load_liquid(liquid=water, volume=100)
    
    # Load inserts into plate wells
    for i in range(1, 25):
        if i <= 12:
            well_name = "A" + str(i)
        else:
            well_name = "B" + str(i-12)
        inserts_plate[well_name].load_liquid(liquid=inserts[i], volume=100)
    
    # Set up ligation reactions
    for i in range(1, 25):
        # Determine destination well
        if i <= 12:
            dest_well = "A" + str(i)
        else:
            dest_well = "B" + str(i-12)
        # Determine source insert well
        if i <= 12:
            src_insert_well = "A" + str(i)
        else:
            src_insert_well = "B" + str(i-12)
        
        # Pick up tip
        p300.pick_up_tip()
        
        # Add buffer (2 ul)
        p300.aspirate(2, block["A1"])
        p300.dispense(2, plate[dest_well])
        
        # Add ligase (1 ul)
        p300.aspirate(1, block["A2"])
        p300.dispense(1, plate[dest_well])
        
        # Add vector (3 ul)
        p300.aspirate(3, block["A3"])
        p300.dispense(3, plate[dest_well])
        
        # Add insert (5 ul)
        p300.aspirate(5, inserts_plate[src_insert_well])
        p300.dispense(5, plate[dest_well])
        
        # Add water (9 ul)
        p300.aspirate(9, block["A4"])
        p300.dispense(9, plate[dest_well])
        
        # Drop tip
        p300.drop_tip()
