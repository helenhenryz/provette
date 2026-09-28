from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 5ul from each of 48 libraries into a tube",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids and load them into wells
    for i in range(1, 49):
        col_idx = (i-1) % 8
        row_idx = (i-1) // 8
        col_letter = chr(ord('A') + col_idx)
        well_name = f"{col_letter}{row_idx+1}"
        # Define the liquid and load it
        lib_liquid = protocol.define_liquid(
            name=f"library {i}",
            description=f"Library {i}",
            display_color="#FF0000"
        )
        plate.well(well_name).load_liquid(liquid=lib_liquid, volume=10)  # starting volume

    # Destination tube
    pool_tube = tubes["A1"]

    # Transfer 5 ul from each library to the pool tube
    for i in range(1, 49):
        col_idx = (i-1) % 8
        row_idx = (i-1) // 8
        col_letter = chr(ord('A') + col_idx)
        well_name = f"{col_letter}{row_idx+1}"
        src_well = plate.well(well_name)
        # Pick up a fresh tip
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, pool_tube)
        p20.drop_tip()
    # Mix the pooled tube to ensure homogeneity
    p20.mix(5, 192, pool_tube)
