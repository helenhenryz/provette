from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tiprack_300])
    
    # Define liquids
    bradford = protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000")
    standards = {}
    for i in range(1, 9):
        standards[f"standard {i}"] = protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#00FF00")
    samples = {}
    for i in range(1, 21):
        samples[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#0000FF")
    
    # Load standards into column 6 of the plate (wells A6-H6)
    for row_idx in range(8):
        well = plate[f"{chr(65+row_idx)}6"]
        well.load_liquid(liquid=standards[f"standard {row_idx+1}"], volume=10)
    
    # Load samples into tube rack wells
    sample_well_names = [
        "A1","A2","A3","A4","A5","A6",
        "B1","B2","B3","B4","B5","B6",
        "C1","C2","C3","C4","C5","C6",
        "D1","D2"
    ]
    for idx, well_name in enumerate(sample_well_names):
        well = tube_rack[well_name]
        well.load_liquid(liquid=samples[f"sample {idx+1}"], volume=1000)
    
    # Load Bradford reagent into reservoir well A1
    reservoir["A1"].load_liquid(liquid=bradford, volume=15000)
    
    # Destination wells for the 20 samples (duplicate in columns 1-5)
    dest_wells = []
    for col in range(5):
        for row_idx in range(8):
            row_letter = chr(65 + row_idx)
            dest_wells.append(plate[f"{row_letter}{col+1}"])
    
    # Transfer each sample (5 µL) in duplicate to two destination wells
    for sample_idx in range(20):
        src_well_name = sample_well_names[sample_idx]
        src_well = tube_rack[src_well_name]
        dest1 = dest_wells[2*sample_idx]
        dest2 = dest_wells[2*sample_idx+1]
        
        # First replicate
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest1)
        p20.drop_tip()
        
        # Second replicate
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest2)
        p20.drop_tip()
    
    # Add 250 µL Bradford reagent to each used well (48 wells total)
    standard_wells = [plate[f"{chr(65+row)}6"] for row in range(8)]
    all_dest_wells = dest_wells + standard_wells
    
    for well in all_dest_wells:
        p300_multi.pick_up_tip()
        p300_multi.aspirate(250, reservoir["A1"])
        p300_multi.dispense(250, well)
        p300_multi.drop_tip()
