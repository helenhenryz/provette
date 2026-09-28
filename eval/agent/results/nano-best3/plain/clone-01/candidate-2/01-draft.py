from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digests", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    temp_module = protocol.load_module("temperature module gen2", 3)
    tube_rack = temp_module.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x buffer", display_color="#0000FF")
    enzyme = protocol.define_liquid(name="enzyme", description="restriction enzyme", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#00FFFF")
    plasmid_liquids = {}
    for i in range(1,13):
        plasmid_liquids[f"plasmid {i}"] = protocol.define_liquid(name=f"plasmid {i}", description=f"Plasmid {i}", display_color="#000000")
    
    # Load liquids into source wells
    # Plasmid wells A1-A12
    for i in range(1,13):
        tube_rack[f"A{i}"].load_liquid(liquid=plasmid_liquids[f"plasmid {i}"], volume=100)
    # Buffer in B1
    tube_rack["B1"].load_liquid(liquid=buffer, volume=100)
    # Enzyme in B2
    tube_rack["B2"].load_liquid(liquid=enzyme, volume=100)
    # Water in B3
    tube_rack["B3"].load_liquid(liquid=water, volume=200)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Perform digests for each of the 12 wells
    for i in range(1,13):
        dest_well = plate[f"A{i}"]
        p20.pick_up_tip()
        # Add 2 ul buffer
        p20.aspirate(2, tube_rack["B1"])
        p20.dispense(2, dest_well)
        # Add 1 ul enzyme
        p20.aspirate(1, tube_rack["B2"])
        p20.dispense(1, dest_well)
        # Add 5 ul plasmid i
        p20.aspirate(5, tube_rack[f"A{i}"])
        p20.dispense(5, dest_well)
        # Add 12 ul water
        p20.aspirate(12, tube_rack["B3"])
        p20.dispense(12, dest_well)
        p20.drop_tip()
