import math
from opentrons import protocol_api

metadata = {"protocolName": "Normalize 24 DNA samples to 10 ng/ul in 50 ul", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    
    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack_300])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    # samples 1-24
    sample_liquids = {}
    for i in range(1, 25):
        name = f"sample {i}"
        liq = protocol.define_liquid(name=name, description=f"DNA sample {i}", display_color="#FF0000")
        sample_liquids[i] = liq
    
    # Load liquids (starting volumes)
    # Water reservoir well A1
    water_reservoir["A1"].load_liquid(liquid=water, volume=15000)  # enough
    
    # Source plate wells A1..X? we have 24 samples in column order A1..A? Actually 24 wells: A1..A12 then B1..B12? According to order: down columns then rows? They said reading down columns or along rows; typical column-wise: A1, B1,... H1, A2,... We'll just assign first 24 wells in order A1..A12 then B1..B12.
    well_order = []
    for col in range(1, 13):  # 1-12
        for row in range(8):  # A-H
            well = chr(65+row) + str(col)
            well_order.append(well)
            if len(well_order) == 24:
                break
        if len(well_order) == 24:
            break
    
    for i, well in enumerate(well_order, start=1):
        source_plate[well].load_liquid(liquid=sample_liquids[i], volume=100)  # reasonable starting vol
    
    # Normalization volumes from normalise tool
    norm_vols = [
        (5.88, 44.12),
        (4.17, 45.83),
        (11.36, 38.64),
        (7.46, 42.54),
        (2.38, 47.62),
        (5.26, 44.74),
        (15.15, 34.85),
        (3.33, 46.67),
        (6.41, 43.59),
        (8.33, 41.67),
        (4.95, 45.05),
        (9.09, 40.91),
        (2.63, 47.37),
        (6.94, 43.06),
        (10.42, 39.58),
        (3.85, 46.15),
        (5.68, 44.32),
        (20.0, 30.0),
        (7.81, 42.19),
        (4.55, 45.45),
        (12.82, 37.18),
        (2.86, 47.14),
        (5.43, 44.57),
        (8.62, 41.38)
    ]
    
    # Add water first using p300, one tip for all wells (optional tip change between wells not needed)
    p300.pick_up_tip()
    for idx, (sample_vol, water_vol) in enumerate(norm_vols):
        dest_well = well_order[idx]
        p300.transfer(water_vol, water_reservoir["A1"], dest_plate[dest_well], new_tip='never', mix_after=(5, 20))
    p300.drop_tip()
    
    # Add each sample with fresh tip
    for idx, (sample_vol, water_vol) in enumerate(norm_vols):
        src_well = well_order[idx]
        dest_well = well_order[idx]
        p20.pick_up_tip()
        p20.transfer(sample_vol, source_plate[src_well], dest_plate[dest_well], new_tip='never', mix_after=(5, 20))
        p20.drop_tip()
    
