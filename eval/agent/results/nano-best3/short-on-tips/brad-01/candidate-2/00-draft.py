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
    protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000")
    for i in range(1, 9):
        protocol.define_liquid(name=f"standard {i}", description=f"BSA standard {i}", display_color="#00FF00")
    for i in range(1, 21):
        protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#0000FF")
    
    # Load standards into plate (column 6)
    for i in range(1, 9):
        well = plate[f"{chr(64+i)}6"]
        well.load_liquid(liquid=f"standard {i}", volume=10)
    
    # Load samples into tube rack
    for i in range(1, 21):
        if i <= 12:
            src_well = tube_rack[f"A{i}"]
        else:
            src_well = tube_rack[f"B{i-12}"]
        src_well.load_liquid(liquid=f"sample {i}", volume=1000)
    
    # Load Bradford reagent into reservoir
    reservoir["A1"].load_liquid(liquid="bradford", volume=15000)
    
    # Generate destination wells for samples (columns 1-5)
    dest_wells = []
    for col in range(5):
        for row_idx in range(8):
            row_letter = chr(65 + row_idx)
            well_name = f"{row_letter}{col+1}"
            dest_wells.append(plate[well_name])
    
    # Transfer samples (5 ul each, duplicate)
    for sample_idx in range(20):
        # Determine source tube
        if sample_idx < 12:
            src_well_name = f"A{sample_idx+1}"
        else:
            src_well_name = f"B{sample_idx-11}"
        src_well = tube_rack[src_well_name]
        
        # Two destination wells per sample
        dest1 = dest_wells[2*sample_idx]
        dest2 = dest_wells[2*sample_idx+1]
        
        # First transfer
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest1)
        p20.drop_tip()
        
        # Second transfer
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dest2)
        p20.drop_tip()
    
    # Add Bradford reagent (250 ul) to all used wells (48 total)
    all_dest_wells = dest_wells + [plate[f"{chr(65+row)}6"] for row in range(8)]
    for i in range(0, len(all_dest_wells), 8):
        chunk = all_dest_wells[i:i+8]
        p300_multi.pick_up_tip()
        p300_multi.aspirate(250, reservoir["A1"])
        p300_multi.dispense(250, chunk)
        p300_multi.drop_tip()
