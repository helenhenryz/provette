from opentrons import protocol_api

metadata = {"protocolName": "Pool 5 ul from each of 48 libraries into a tube", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define library liquids
    for i in range(1, 49):
        lib_name = f"library {i}"
        lib_obj = protocol.define_liquid(name=lib_name, description=f"Library {i}", display_color="#FF0000")
        letters = "ABCDEF"
        col_idx = (i-1) // 8
        row_idx = (i-1) % 8 + 1
        well_label = letters[col_idx] + str(row_idx)
        plate[well_label].load_liquid(liquid=lib_obj, volume=10)

    # Pool 5 ul from each library into tube rack A1
    p20.pick_up_tip()
    for i in range(1, 49):
        letters = "ABCDEF"
        col_idx = (i-1) // 8
        row_idx = (i-1) % 8 + 1
        well_label = letters[col_idx] + str(row_idx)
        src_well = plate[well_label]
        p20.aspirate(5, src_well)
        p20.dispense(5, tubes["A1"])
        p20.blow_out()
    # Mix the pooled library
    p20.mix(5, 10, tubes["A1"])
    p20.drop_tip()
