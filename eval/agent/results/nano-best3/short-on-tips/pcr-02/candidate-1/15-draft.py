from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup with master mix, water, and 24 samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Define liquids and keep references
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2x PCR master mix with primers",
        display_color="#FF6600"
    )
    water = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#0000FF"
    )
    samples = {}
    for i in range(1, 25):
        samples[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color="#00FF00"
        )
    
    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=master_mix, volume=300)
    reservoir["A2"].load_liquid(liquid=water, volume=300)
    
    # Manually define the 24 well names in the tube rack
    sample_well_names = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6","C1","C2","C3","C4","C5","C6","D1","D2","D3","D4","D5","D6"]
    for i, well_name in enumerate(sample_well_names):
        tube_rack[well_name].load_liquid(liquid=samples[f"sample {i+1}"], volume=10)
    
    # Load single-channel pipette for master mix and water distribution
    p300_single = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Prepare destination wells (24 wells in columns A and B)
    dest_wells = []
    for col in ["A", "B"]:
        for row in range(1, 13):
            dest_wells.append(plate[f"{col}{row}"])
    
    # Step 1: Distribute master mix (12.5 ul) to each destination well
    p300_single.transfer(
        volume=12.5,
        source=reservoir["A1"],
        dest=dest_wells,
        new_tip="always"
    )
    
    # Step 2: Distribute water (10.5 ul) to each destination well
    p300_single.transfer(
        volume=10.5,
        source=reservoir["A2"],
        dest=dest_wells,
        new_tip="always"
    )
    
    # Load multi-channel pipette for DNA transfers on left mount
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])
    
    # Step 3: Add 2 ul of DNA from each sample to the corresponding well
    source_wells = sample_well_names
    batch1_sources = source_wells[:12]
    batch2_sources = source_wells[12:]
    batch1_dests = dest_wells[:12]
    batch2_dests = dest_wells[12:]
    
    # First batch of DNA transfers
    p300_multi.pick_up_tip()
    for i in range(len(batch1_sources)):
        p300_multi.aspirate(2, batch1_sources[i])
        p300_multi.dispense(2, batch1_dests[i])
    p300_multi.drop_tip()
    
    # Second batch of DNA transfers
    p300_multi.pick_up_tip()
    for i in range(len(batch2_sources)):
        p300_multi.aspirate(2, batch2_sources[i])
        p300_multi.dispense(2, batch2_dests[i])
    p300_multi.drop_tip()
