from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 25 ul from each of 96 indexed sequencing libraries into a single tube",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 3)
    
    # Load instrument
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])
    
    # Define liquids (libraries 1-96) and load them into plate wells
    for i in range(1, 97):
        lib_name = f"library {i}"
        lib_obj = protocol.define_liquid(
            name=lib_name,
            description=f"Library {i} sequencing library",
            display_color="#0000FF"
        )
        well = plate.wells()[i-1]  # 0-indexed wells
        well.load_liquid(liquid=lib_obj, volume=100)
    
    # Destination tube
    dest = tubes["A1"]
    
    # Pool 25 ul from each well into the destination tube
    p300.pick_up_tip()
    for source_well in plate.wells():
        p300.aspirate(25, source_well)
        p300.dispense(25, dest)
    # Mix the final pool to ensure homogeneity
    p300.mix(5, 1920, dest)
    p300.drop_tip()
