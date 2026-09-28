import math
from opentrons import protocol_api

metadata = {"protocolName": "Normalize DNA samples to 10 ng/ul in 50 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)   # samples
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)   # normalized samples
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)          # water in well A1

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # define liquids
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    # samples
    sample_liquids = {}
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"DNA sample {i}", display_color="#FF0000")
        sample_liquids[i] = liq

    # load liquids (starting volumes)
    # source wells A1-A24 each have 100 ul of sample
    for i in range(1, 25):
        well = source_plate.wells_by_name()[f"A{i}"]
        well.load_liquid(sample_liquids[i], 100)

    # water reservoir well A1 has 20000 ul
    reservoir_well = reservoir.wells_by_name()["A1"]
    reservoir_well.load_liquid(water, 20000)

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
        src_well = source_plate.wells_by_name()[f"A{idx}"]
        dst_well = dest_plate.wells_by_name()[f"A{idx}"]

        p300.pick_up_tip()
        # aspirate water then sample
        p300.aspirate(water_ul, reservoir_well)
        p300.aspirate(sample_ul, src_well)
        p300.dispense(water_ul + sample_ul, dst_well)
        p300.mix(3, 25, dst_well)  # optional mixing
        p300.drop_tip()
