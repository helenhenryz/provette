from opentrons import protocol_api

metadata = {
    "protocolName": "Normalize 48 sequencing libraries to 4 nM",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Define liquids
    buffer_liquid = protocol.define_liquid(
        name="buffer",
        description="Elution buffer",
        display_color="#0000FF"
    )
    reservoir["A1"].load_liquid(liquid=buffer_liquid, volume=10000)
    
    for i in range(48):
        lib_liquid = protocol.define_liquid(
            name=f"library {i+1}",
            description=f"Library {i+1}",
            display_color="#000000"
        )
        source_plate.wells()[i].load_liquid(liquid=lib_liquid, volume=100)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Define library and buffer volumes (ul)
    library_volumes = [
        6.67, 1.78, 10, 1, 2.42, 14.55, 1.33, 3.81, 5.71, 8.89, 1.11, 2.96,
        13.33, 2, 4.44, 1.45, 7.27, 2.67, 10.67, 1.23, 3.33, 5, 1.67, 8,
        2.22, 6.15, 1.14, 3.64, 9.41, 1.6, 2.76, 4.21, 1.9, 5.33, 1.29,
        3.2, 12.31, 2.11, 4.71, 1.05, 4, 8.42, 1.38, 2.58, 6.4, 1.82,
        3.48, 11.43
    ]
    buffer_volumes = [
        13.33, 18.22, 10, 19, 17.58, 5.45, 18.67, 16.19, 14.29, 11.11, 18.89,
        17.04, 6.67, 18, 15.56, 18.55, 12.73, 17.33, 9.33, 18.77, 16.67,
        17.78, 13.85, 18.86, 10.59, 18.4, 17.24, 15.79, 18.1, 14.67, 18.71,
        16.8, 7.69, 17.89, 16, 11.58, 18.62, 17.42, 15.29, 18.95, 16,
        11.58, 18.62, 17.42, 13.6, 18.18, 16.52, 8.57
    ]
    
    # Perform transfers
    for i in range(48):
        src_well = source_plate.wells()[i]
        dest_well = dest_plate.wells()[i]
        lib_vol = library_volumes[i]
        buf_vol = buffer_volumes[i]
        p20.pick_up_tip()
        p20.aspirate(lib_vol, src_well)
        p20.dispense(lib_vol, dest_well)
        p20.aspirate(buf_vol, reservoir["A1"])
        p20.dispense(buf_vol, dest_well)
        p20.drop_tip()
