import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "BCA assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips1 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips2 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)  # second rack
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    src_samples = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips1, tips2])

    # define liquids
    reagent = protocol.define_liquid(name="reagent", description="BCA working reagent", display_color="#FF0000")
    bsa = protocol.define_liquid(name="bsa", description="2 mg/ml BSA stock", display_color="#00FF00")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#0000FF")
    samples = {}
    for i in range(1, 41):
        name = f"sample {i}"
        liq = protocol.define_liquid(name=name, description=f"Protein sample {i}", display_color="#FFA500")
        samples[name] = liq

    # load liquids onto deck
    tuberack["A1"].load_liquid(liquid=bsa, volume=1500)  # BSA stock
    tuberack["A2"].load_liquid(liquid=water, volume=1500)  # water
    reservoir["A1"].load_liquid(liquid=reagent, volume=15000)  # reagent
    for i in range(1, 41):
        col = (i-1) // 8 + 1
        row = ((i-1) % 8)
        well = chr(65+row) + str(col)
        src_samples[well].load_liquid(liquid=samples[f"sample {i}"], volume=200)

    # ---- transfer samples to destination plate (duplicate) ----
    for i in range(1, 41):
        col_src = (i-1) // 8 + 1
        row_src = ((i-1) % 8)
        well_src = chr(65+row_src) + str(col_src)
        # destinations: two consecutive wells in column‑wise order
        dst_index = (i-1)*2
        dst_row = dst_index // 12
        dst_col = (dst_index % 12) + 1
        well_dst1 = chr(65+dst_row) + str(dst_col)
        dst_index2 = dst_index + 1
        dst_row2 = dst_index2 // 12
        dst_col2 = (dst_index2 % 12) + 1
        well_dst2 = chr(65+dst_row2) + str(dst_col2)
        p300.transfer(25, src_samples[well_src], dst_plate[well_dst1])
        p300.transfer(25, src_samples[well_src], dst_plate[well_dst2])

    # ---- prepare standards (BSA dilutions) directly in destination plate ----
    std_start_idx = 80  # after samples
    for i in range(8):  # i = 0..7
        stock_vol = 25.0 / (2 ** i)  # ul of BSA stock
        water_vol = 25.0 - stock_vol  # ul of water
        for rep in range(2):  # duplicate
            idx = std_start_idx + i*2 + rep
            dst_row = idx // 12
            dst_col = (idx % 12) + 1
            dst_well = chr(65+dst_row) + str(dst_col)
            if stock_vol > 0:
                p300.transfer(stock_vol, tuberack["A1"], dst_plate[dst_well], mix_after=(2, 25))
            if water_vol > 0:
                p300.transfer(water_vol, tuberack["A2"], dst_plate[dst_well], mix_after=(2, 25))

    # ---- add 200 ul reagent to all used wells (96 wells) ----
    for i in range(96):
        row = i // 12
        col = (i % 12) + 1
        well = chr(65+row) + str(col)
        p300.transfer(200, reservoir["A1"], dst_plate[well])
