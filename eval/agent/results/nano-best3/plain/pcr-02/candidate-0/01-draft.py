from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup 25ul reactions",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    sample_tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    master_mix_tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2x PCR master mix with primers",
        display_color="#FF6600"
    )
    water = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#0000FF"
    )
    sample_liquids = {}
    for i in range(1, 25):
        sample_liquids[i] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color="#808080"
        )
    
    # Load liquids onto deck
    # Master mix: 500 ul in master_mix_tubes["A1"]
    master_mix_tubes["A1"].load_liquid(liquid=master_mix, volume=500)
    # Water: 600 ul in reservoir["A1"] (increase volume to avoid shallow aspiration)
    reservoir["A1"].load_liquid(liquid=water, volume=600)
    # Samples: 10 ul each in corresponding wells of sample_tubes
    for i in range(1, 25):
        if i <= 6:
            well_name = f"A{i}"
        elif i <= 12:
            well_name = f"B{i-6}"
        elif i <= 18:
            well_name = f"C{i-12}"
        else:
            well_name = f"D{i-18}"
        sample_tubes[well_name].load_liquid(liquid=sample_liquids[i], volume=10)
    
    # Define target wells (the 24 wells we will fill)
    target_well_names = [
        "A1","A2","A3","A4","A5","A6",
        "B1","B2","B3","B4","B5","B6",
        "C1","C2","C3","C4","C5","C6",
        "D1","D2","D3","D4","D5","D6"
    ]
    
    # Transfers
    for i, well_name in enumerate(target_well_names, start=1):
        target_well = plate[well_name]
        # Determine source well for sample i
        if i <= 6:
            sample_source = sample_tubes[f"A{i}"]
        elif i <= 12:
            sample_source = sample_tubes[f"B{i-6}"]
        elif i <= 18:
            sample_source = sample_tubes[f"C{i-12}"]
        else:
            sample_source = sample_tubes[f"D{i-18}"]
        
        # Add 12.5 ul master mix
        p20.pick_up_tip()
        p20.aspirate(12.5, master_mix_tubes["A1"])
        p20.dispense(12.5, target_well)
        p20.drop_tip()
        
        # Add 10.5 ul water
        p20.pick_up_tip()
        p20.aspirate(10.5, reservoir["A1"])
        p20.dispense(10.5, target_well)
        p20.drop_tip()
        
        # Add 2 ul sample
        p20.pick_up_tip()
        p20.aspirate(2, sample_source)
        p20.dispense(2, target_well)
        # Mix after sample addition
        p20.pick_up_tip()
        p20.mix(5, 20, target_well)
        p20.drop_tip()
