from opentrons import protocol_api

metadata = {
    "protocolName": "Ligation reactions 24 x 20ul",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip rack
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    # Load temperature module and aluminum block
    temp_module = protocol.load_module("temperature module gen2", "2")
    cold_block_tubes = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    # Load PCR plate
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", "3")
    # Load insert plate (96-well plate with inserts)
    insert_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "5")
    # Load reservoir for water
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", "4")
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    buffer_liquid = protocol.define_liquid(
        name="buffer",
        description="10x T4 DNA ligase buffer",
        display_color="#0000FF"
    )
    ligase_liquid = protocol.define_liquid(
        name="ligase",
        description="T4 DNA ligase",
        display_color="#00FF00"
    )
    vector_liquid = protocol.define_liquid(
        name="vector",
        description="cut vector",
        display_color="#FF0000"
    )
    water_liquid = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#00FFFF"
    )
    
    # Define insert liquids (insert 1 to insert 24) and store them
    insert_liquids = {}
    for i in range(1, 25):
        insert_name = f"insert {i}"
        insert_liquids[i] = protocol.define_liquid(
            name=insert_name,
            description=f"Insert {i}",
            display_color="#808080"
        )
    
    # Load liquids into source wells
    # Buffer, ligase, vector into cold block wells
    cold_block_tubes["A1"].load_liquid(liquid=buffer_liquid, volume=100)
    cold_block_tubes["A2"].load_liquid(liquid=ligase_liquid, volume=100)
    cold_block_tubes["A3"].load_liquid(liquid=vector_liquid, volume=100)
    # Water into reservoir
    water_reservoir["A1"].load_liquid(liquid=water_liquid, volume=500)
    
    # Load insert liquids into insert plate wells
    # Generate first 24 well names in column-major order (A1-A8, B1-B8, C1-C8)
    insert_well_names = []
    for col in ["A", "B", "C"]:
        for row in range(1, 9):
            insert_well_names.append(col + str(row))
    
    # Load each insert liquid into its well with 20 ul starting volume
    for i, well_name in enumerate(insert_well_names, start=1):
        insert_plate[well_name].load_liquid(
            liquid=insert_liquids[i],
            volume=20
        )
    
    # Loop over the 24 reactions
    for i, well_name in enumerate(insert_well_names, start=1):
        # Destination well in the PCR plate
        dest_well = plate[well_name]
        # Source wells
        buffer_src = cold_block_tubes["A1"]
        ligase_src = cold_block_tubes["A2"]
        vector_src = cold_block_tubes["A3"]
        insert_src = insert_plate[well_name]  # same well name as source
        water_src = water_reservoir["A1"]
        
        # Pick up a tip
        p20.pick_up_tip()
        
        # Add buffer (2 ul)
        p20.aspirate(2, buffer_src)
        p20.dispense(2, dest_well)
        
        # Add ligase (1 ul)
        p20.aspirate(1, ligase_src)
        p20.dispense(1, dest_well)
        
        # Add vector (3 ul)
        p20.aspirate(3, vector_src)
        p20.dispense(3, dest_well)
        
        # Add insert (5 ul)
        p20.aspirate(5, insert_src)
        p20.dispense(5, dest_well)
        
        # Add water (9 ul)
        p20.aspirate(9, water_src)
        p20.dispense(9, dest_well)
        
        # Mix the final 20 ul
        p20.mix(20, 3, dest_well)
        
        # Drop tip
        p20.drop_tip()
