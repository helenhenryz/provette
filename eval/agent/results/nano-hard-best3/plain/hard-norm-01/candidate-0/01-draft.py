from opentrons import protocol_api

metadata = {
    "protocolName": "Normalization of 48 libraries to 4 nM",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    buffer = protocol.define_liquid(
        name="buffer", description="elution buffer", display_color="#0000FF"
    )
    # Load buffer into reservoir
    reservoir["A1"].load_liquid(liquid=buffer, volume=1000)
    
    # Define library liquids
    library_liquids = {}
    for i in range(1, 49):
        lib_liquid = protocol.define_liquid(
            name=f"library {i}",
            description=f"Library {i}",
            display_color="#000000"
        )
        library_liquids[i] = lib_liquid
    
    # Load library liquids into source plate wells
    source_well_names = [
        "A1","A2","A3","A4","A5","A6","A7","A8",
        "B1","B2","B3","B4","B5","B6","B7","B8",
        "C1","C2","C3","C4","C5","C6","C7","C8",
        "D1","D2","D3","D4","D5","D6","D7","D8",
        "E1","E2","E3","E4","E5","E6","E7","E8",
        "F1","F2","F3","F4","F5","F6","F7","F8"
    ]
    # Load each library into its source well with 100 ul
    for i in range(48):
        lib_liquid = library_liquids[i+1]
        well = source_plate[source_well_names[i]]
        well.load_liquid(liquid=lib_liquid, volume=100)
    
    # Define library volumes (ul) as per plate map
    library_volumes = [
        6.67, 1.78, 10.0, 1.0, 2.42, 14.55, 1.33, 3.81, 5.71, 8.89,
        1.11, 2.96, 13.33, 2.0, 4.44, 1.45, 7.27, 2.67, 10.67, 1.23,
        3.33, 5.0, 1.67, 8.0, 2.22, 6.15, 1.14, 3.64, 9.41, 1.6,
        2.76, 4.21, 1.9, 5.33, 1.29, 3.2, 12.31, 2.11, 4.71, 1.05,
        4.0, 8.42, 1.38, 2.58, 6.4, 1.82, 3.48, 11.43
    ]
    
    # Destination well order (same as source well order)
    dest_well_names = source_well_names
    
    # Normalize: for each library i, transfer to dest plate
    for i in range(48):
        lib_vol = library_volumes[i]
        buf_vol = 20 - lib_vol
        src_well = source_plate[source_well_names[i]]
        dest_well = dest_plate[dest_well_names[i]]
        
        # Pick up tip
        p20.pick_up_tip()
        # Aspirate buffer first (fresh tip)
        p20.aspirate(buf_vol, reservoir["A1"])
        # Aspirate library
        p20.aspirate(lib_vol, src_well)
        # Dispense total volume into destination well with mixing
        p20.dispense(lib_vol + buf_vol, dest_well, mix_after=(5, 16))
        # Drop tip
        p20.drop_tip()
