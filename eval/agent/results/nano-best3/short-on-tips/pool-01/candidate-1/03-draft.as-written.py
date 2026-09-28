from opentrons import protocol_api

metadata = {"protocolName": "Pool 5 ul from each of 48 libraries into a tube", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_200ul", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    p300 = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tips])
    
    p300.pick_up_tip()
    
    # Define library liquids and load 10 ul into each well
    for i in range(1, 49):
        lib_name = f"library {i}"
        lib_obj = protocol.define_liquid(name=lib_name, description=f"Library {i}", display_color="#FF0000")
        letters = "ABCDEF"
        col_idx = (i-1) // 8
        row_idx = (i-1) % 8 + 1
        well_label = letters[col_idx] + str(row_idx)
        plate[well_label].load_liquid(liquid=lib_obj, volume=10)
    
    # Pool 5 ul from each library into tube A1 in batches of 8 wells
    for batch_start in range(0, 48, 8):
        batch_wells = []
        for j in range(8):
            idx = batch_start + j
            if idx >= 48:
                break
            letters = "ABCDEF"
            col_idx = idx // 8
            row_idx = idx % 8 + 1
            well_label = letters[col_idx] + str(row_idx)
            batch_wells.append(plate[well_label])
        p300.aspirate(5, batch_wells)
        p300.dispense(5, tubes["A1"])
    
    # Mix the pooled library
    p300.mix(5, 192, tubes["A1"])
    p300.drop_tip()
