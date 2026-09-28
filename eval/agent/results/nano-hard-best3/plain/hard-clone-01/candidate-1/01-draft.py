from opentrons import protocol_api

metadata = {"protocolName": "Ligation Setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack1 = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    tip_rack2 = protocol.load_labware("opentrons_96_tiprack_20ul", "6")
    insert_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "2")
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", "3")
    temp_mod = protocol.load_module("temperature module gen2", "4")
    cold_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")
    
    # Load instrument
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack1, tip_rack2])
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x T4 DNA ligase buffer", display_color="#0000FF")
    ligase = protocol.define_liquid(name="ligase", description="T4 DNA ligase", display_color="#00FF00")
    vector = protocol.define_liquid(name="vector", description="Cut vector", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    
    # Define inserts
    inserts = {}
    for i in range(1, 25):
        insert_name = f"insert {i}"
        inserts[insert_name] = protocol.define_liquid(name=insert_name, description=f"Insert {i}", display_color="#FFFF00")
    
    # Load liquids into source wells
    cold_block["A1"].load_liquid(liquid=buffer, volume=52.8)
    cold_block["A2"].load_liquid(liquid=ligase, volume=26.4)
    cold_block["A3"].load_liquid(liquid=vector, volume=79.2)
    water_reservoir["A1"].load_liquid(liquid=water, volume=237.6)
    
    # Load inserts into plate wells
    for i in range(1, 25):
        insert_name = f"insert {i}"
        if i <= 12:
            well_name = f"A{i}"
        else:
            well_name = f"B{i-12}"
        insert_plate[well_name].load_liquid(liquid=inserts[insert_name], volume=10)
    
    # Set temperature to 4°C
    temp_mod.set_temperature(4)
    
    # Perform 24 ligation reactions
    for i in range(1, 25):
        # Determine destination well
        if i <= 12:
            dest_well = dest_plate[f"A{i}"]
        else:
            dest_well = dest_plate[f"B{i-12}"]
        
        # Water (9 ul) first
        p20.pick_up_tip()
        p20.aspirate(9, water_reservoir["A1"])
        p20.dispense(9, dest_well)
        p20.drop_tip()
        
        # Buffer (2 ul) second
        p20.pick_up_tip()
        p20.aspirate(2, cold_block["A1"])
        p20.dispense(2, dest_well)
        p20.drop_tip()
        
        # Insert (5 ul) third
        insert_name = f"insert {i}"
        if i <= 12:
            insert_well = insert_plate[f"A{i}"]
        else:
            insert_well = insert_plate[f"B{i-12}"]
        p20.pick_up_tip()
        p20.aspirate(5, insert_well)
        p20.dispense(5, dest_well)
        p20.drop_tip()
        
        # Vector (3 ul) fourth
        p20.pick_up_tip()
        p20.aspirate(3, cold_block["A3"])
        p20.dispense(3, dest_well)
        p20.drop_tip()
        
        # Ligase (1 ul) last
        p20.pick_up_tip()
        p20.aspirate(1, cold_block["A2"])
        p20.dispense(1, dest_well)
        p20.drop_tip()
