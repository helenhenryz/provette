from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digests", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and aluminium block
    temp_mod = protocol.load_module("temperature module gen2", 1)
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    
    # Set temperature to 4°C
    temp_mod.set_temperature(4)
    
    # Load PCR plate and tip rack
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    buffer_liquid = protocol.define_liquid(
        name="buffer", description="10x restriction enzyme buffer", display_color="#0000FF"
    )
    enzyme_liquid = protocol.define_liquid(
        name="enzyme", description="Restriction enzyme", display_color="#00FF00"
    )
    water_liquid = protocol.define_liquid(
        name="water", description="Molecular grade water", display_color="#FFFFFF"
    )
    plasmid_liquids = {}
    for i in range(1, 13):
        plasmid_liquids[i] = protocol.define_liquid(
            name=f"plasmid {i}", description=f"Plasmid {i}", display_color="#FF0000"
        )
    
    # Load liquids into source wells
    block["A1"].load_liquid(liquid=buffer_liquid, volume=30)
    block["A2"].load_liquid(liquid=enzyme_liquid, volume=20)
    block["A3"].load_liquid(liquid=water_liquid, volume=200)  # increased to 200 ul to provide margin
    plasmid_source_wells = ["A4", "A5", "A6", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3"]
    for i, well_name in enumerate(plasmid_source_wells, start=1):
        plasmid_liquid = plasmid_liquids[i]
        block[well_name].load_liquid(liquid=plasmid_liquid, volume=10)
    
    # Set up transfers for 12 restriction digests
    for i in range(1, 13):
        # Add 12 ul water
        p20.pick_up_tip()
        p20.aspirate(12, block["A3"])
        p20.dispense(12, plate[f"A{i}"])
        p20.drop_tip()
        
        # Add 2 ul buffer
        p20.pick_up_tip()
        p20.aspirate(2, block["A1"])
        p20.dispense(2, plate[f"A{i}"])
        p20.drop_tip()
        
        # Add 5 ul plasmid
        p20.pick_up_tip()
        p20.aspirate(5, block[plasmid_source_wells[i-1]])
        p20.dispense(5, plate[f"A{i}"])
        p20.drop_tip()
        
        # Add 1 ul enzyme with mixing
        p20.pick_up_tip()
        p20.aspirate(1, block["A2"])
        p20.dispense(1, plate[f"A{i}"], mix_after=(5, 16))
        p20.drop_tip()
    
    # Deactivate temperature module
    temp_mod.deactivate()
