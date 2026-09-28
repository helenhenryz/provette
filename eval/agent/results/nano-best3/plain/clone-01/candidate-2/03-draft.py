from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digests", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x buffer", display_color="#0000FF")
    enzyme = protocol.define_liquid(name="enzyme", description="restriction enzyme", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#00FFFF")
    
    # Define plasmid liquids
    plasmid_liquids = {}
    for i in range(1,13):
        plasmid_liquids[f"plasmid {i}"] = protocol.define_liquid(name=f"plasmid {i}", description=f"Plasmid {i}", display_color="#000000")
    
    # Load liquids into source wells
    # Buffer in C1
    tube_rack["C1"].load_liquid(liquid=buffer, volume=100)
    # Enzyme in C2
    tube_rack["C2"].load_liquid(liquid=enzyme, volume=100)
    # Water in C3
    tube_rack["C3"].load_liquid(liquid=water, volume=200)
    
    # Source wells for plasmids: A1, A2, A3, A4, A5, A6, B1, B2, B3, B4, B5, B6
    source_wells = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6"]
    for i, well_name in enumerate(source_wells, start=1):
        tube_rack[well_name].load_liquid(liquid=plasmid_liquids[f"plasmid {i}"], volume=100)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Perform digests for each of the 12 wells
    for i in range(1,13):
        dest_well = plate[f"A{i}"]
        p20.pick_up_tip()
        # Add 2 ul buffer
        p20.aspirate(2, tube_rack["C1"])
        p20.dispense(2, dest_well)
        # Add 1 ul enzyme
        p20.aspirate(1, tube_rack["C2"])
        p20.dispense(1, dest_well)
        # Add 5 ul plasmid i
        plasmid_well = source_wells[i-1]  # "A1" through "B6"
        p20.aspirate(5, tube_rack[plasmid_well])
        p20.dispense(5, dest_well)
        # Add 12 ul water
        p20.aspirate(12, tube_rack["C3"])
        p20.dispense(12, dest_well)
        p20.drop_tip()
