from opentrons import protocol_api

metadata = {"protocolName": "Pool 5 ul from each of 48 libraries into a tube", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip racks
    tips_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_200ul = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20ul])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_200ul])
    
    # Define library liquids and load 10 ul into each well
    for i in range(1, 49):
        lib_name = f"library {i}"
        lib_obj = protocol.define_liquid(name=lib_name, description=f"Library {i}", display_color="#FF0000")
        letters = "ABCDEF"
        col_idx = (i-1) // 8
        row_idx = (i-1) % 8 + 1
        well_label = letters[col_idx] + str(row_idx)
        plate[well_label].load_liquid(liquid=lib_obj, volume=10)
    
    # Pool 5 ul from each library into tube A1 using p20
    for i in range(1, 49):
        lib_name = f"library {i}"
        letters = "ABCDEF"
        col_idx = (i-1) // 8
        row_idx = (i-1) % 8 + 1
        well_label = letters[col_idx] + str(row_idx)
        src_well = plate[well_label]
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, tubes["A1"])
        # On the last library, mix with p300
        if i == 48:
            p300.pick_up_tip()
            p300.mix(5, 192, tubes["A1"])
            p300.drop_tip()
        p20.drop_tip()
