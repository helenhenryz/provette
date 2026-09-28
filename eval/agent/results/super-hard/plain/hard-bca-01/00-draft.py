import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "BCA assay", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    src_samples = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

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
    # BSA stock
    tuberack["A1"].load_liquid(liquid=bsa, volume=1500)  # enough
    # water
    tuberack["A2"].load_liquid(liquid=water, volume=1500)
    # reagent
    reservoir["A1"].load_liquid(liquid=reagent, volume=15000)
    # source samples
    for i in range(1, 41):
        col = (i-1) // 8 + 1  # columns 1-12
        row = ((i-1) % 8)  # rows A-H
        well_name = chr(65+row) + str(col)
        src_samples[well_name].load_liquid(liquid=samples[f"sample {i}"], volume=200)

    # ---- prepare BSA dilution series in tuberack wells B1..B8 ----
    # We'll use tuberack B1-B8 as dilution vessels
    dilution_wells = [f"B{i}" for i in range(1, 9)]  # B1 to B8
    # stock is tuberack A1, diluent water from A2
    p300.pick_up_tip()
    for i, well in enumerate(dilution_wells):
        if i == 0:
            # first well: undiluted BSA stock, just transfer 25 ul stock? Actually need 25 ul total BSA.
            # According to dilution series: add 0 diluent, transfer 25 ul stock? The output said add diluent then transfer in.
            # We'll follow generic: add diluent (0), transfer 25 ul from stock, mix.
            p300.transfer(0, tuberack["A2"], tuberack[well])  # add water 0
            p300.transfer(25, tuberack["A1"], tuberack[well])
        else:
            # add 25 ul water, transfer 25 ul from previous well
            p300.transfer(25, tuberack["A2"], tuberack[well])
            p300.transfer(25, tuberack[dilution_wells[i-1]], tuberack[well])
        p300.mix(3, 25, tuberack[well])
    # after loop, remove excess from last well to waste (25 ul)
    p300.transfer(25, tuberack[dilution_wells[-1]], protocol.trash_container)
    p300.drop_tip()

    # ---- transfer samples to destination plate (duplicate) ----
    sample_ Wells = []
    for i in range(1, 41):
        name = f"sample {i}"
        col = (i-1) // 8 + 1
        row = ((i-1) % 8)
        well_name = chr(65+row) + str(col)
        src = src_samples[well_name]
        # two destinations: calculate index
        idx = (i-1)*2  # 0-based
        row_dst = idx // 12
        col_dst = (idx % 12) + 1
        dst_well1 = chr(65+row_dst) + str(col_dst)
        dst_well2 = chr(65+row_dst+1) + str(col_dst) if (row_dst+1)<8 else chr(65+row_dst-1) + str(col_dst+1)  # simple alternate
        # simpler: fill columnwise first 80 wells: we'll just compute
        # Let's do columnwise fill:
    # Actually easier: fill first 80 wells column-wise A1..A12, B1..B12... until 80.
    # We'll compute directly:
    p300.pick_up_tip()
    for i in range(1, 41):
        name = f"sample {i}"
        col_src = (i-1) // 8 + 1
        row_src = ((i-1) % 8)
        well_src = chr(65+row_src) + str(col_src)
        # destinations: two consecutive wells in column-wise order
        dst_index = (i-1)*2
        dst_row = dst_index // 12
        dst_col = (dst_index % 12) + 1
        well_dst1 = chr(65+dst_row) + str(dst_col)
        # second duplicate: next well in same column if possible else next column
        dst_index2 = dst_index + 1
        dst_row2 = dst_index2 // 12
        dst_col2 = (dst_index2 % 12) + 1
        well_dst2 = chr(65+dst_row2) + str(dst_col2)
        p300.transfer(25, src_samples[well_src], dst_plate[well_dst1], new_tip='never')
        p300.transfer(25, src_samples[well_src], dst_plate[well_dst2], new_tip='never')
    p300.drop_tip()

    # ---- transfer standards (BSA dilutions) duplicate ----
    p300.pick_up_tip()
    std_start_idx = 80  # after samples
    for i, well in enumerate(dilution_wells):
        # duplicate
        for rep in range(2):
            idx = std_start_idx + i*2 + rep
            dst_row = idx // 12
            dst_col = (idx % 12) + 1
            dst_well = chr(65+dst_row) + str(dst_col)
            p300.transfer(25, tuberack[well], dst_plate[dst_well], new_tip='never')
    p300.drop_tip()

    # ---- add 200 ul reagent to all used wells (first 96? actually 80+16=96) ----
    p300.pick_up_tip()
    for i in range(96):
        row = i // 12
        col = (i % 12) + 1
        well = chr(65+row) + str(col)
        p300.transfer(200, reservoir["A1"], dst_plate[well], new_tip='never')
    p300.drop_tip>
