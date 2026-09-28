import math
from opentrons import protocol_api

metadata = {"protocolName": "Normalize DNA samples to 10 ng/ul in 50 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)   # samples
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)   # normalized samples
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)          # water in well A1

    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack_300])

    # define liquids
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    # samples
    sample_liquids = {}
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"DNA sample {i}", display_color="#FF0000")
        sample_liquids[i] = liq

    # load liquids (starting volumes)
    # source wells: map 24 samples across first three columns (cols 1-3), rows A-H
    for i in range(1, 25):
        zero_based = i - 1
        col = (zero_based // 8) + 1          # 1,2,3
        row_idx = zero_based % 8             # 0-7 -> A-H
        row_label = chr(ord('A') + row_idx)
        well_name = f"{row_label}{col}"
        well = source_plate.wells_by_name()[well_name]
        well.load_liquid(sample_liquids[i], 100)  # 100 ul each

    # water reservoir well A1 has enough water (need ~1025 ul, load 2000 ul safely within capacity)
    reservoir_well = reservoir.wells_by_name()["A1"]
    reservoir_well.load_liquid(water, 2000)

    # normalization volumes from normalise function
    norm_data = [
        (5.88, 44.12), (4.17, 45.83), (11.36, 38.64), (7.46, 42.54),
        (2.38, 47.62), (5.26, 44.74), (15.15, 34.85), (3.33, 46.67),
        (6.41, 43.59), (8.33, 41.67), (4.95, 45.05), (9.09, 40.91),
        (2.63, 47.37), (6.94, 43.06), (10.42, 39.58), (3.85, 46.15),
        (5.68, 44.32), (20.0, 30.0), (7.81, 42.19), (4.55, 45.45),
        (12.82, 37.18), (2.86, 47.14), (5.43, 44.57), (8.62, 41.38)
    ]

    for idx, (sample_ul, water_ul) in enumerate(norm_data, start=1):
        # source well mapping same as above
        zero_based = idx - 1
        col_src = (zero_based // 8) + 1
        row_idx_src = zero_based % 8
        row_label_src = chr(ord('A') + row_idx_src)
        src_well_name = f"{row_label_src}{col_src}"
        src_well = source_plate.wells_by_name()[src_well_name]

        # destination well mapping same pattern
        zero_based_dst = idx - 1
        col_dst = (zero_based_dst // 8) + 1
        row_idx_dst = zero_based_dst % 8
        row_label_dst = chr(ord('A') + row_idx_dst)
        dst_well_name = f"{row_label_dst}{col_dst}"
        dst_well = dest_plate.wells_by_name()[dst_well_name]

        # add water with p300
        p300.pick_up_tip()
        p300.aspirate(water_ul, reservoir_well)
        p300.dispense(water_ul, dst_well)
        p300.drop_tip()

        # add sample with p20
        p20.pick_up_tip()
        p20.aspirate(sample_ul, src_well)
        p20.dispense(sample_ul, dst_well)
        p20.drop_tip()

        # optional mixing: ensure homogenous mix
        p300.pick_up_tip()
        p300.mix(5, 40, dst_well)  # 5 cycles of 40 ul (~80% of 50 ul)
        p300.drop_tip()
