from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#0000FF")
    samples = {}
    for i in range(1, 25):
        samples[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color="#000000")
    
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    sample_tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    master_mix_water_tubes = protocol.load_labware("opentrons_12_tuberack_falcon_15ml_conical", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Load liquids into source wells
    master_mix_water_tubes["A1"].load_liquid(liquid=master_mix, volume=500)
    master_mix_water_tubes["A2"].load_liquid(liquid=water, volume=500)
    
    # Load samples into tube rack wells
    well_names = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6","C1","C2","C3","C4","C5","C6","D1","D2","D3","D4","D5","D6"]
    
    # Load samples into tube rack wells
    for i, well in enumerate(well_names, start=1):
        sample_tubes[well].load_liquid(liquid=samples[f"sample {i}"], volume=10)
    
    # Perform transfers for each of the 24 reactions
    for i, well in enumerate(well_names, start=1):
        # Add 12.5 ul master mix
        p20.pick_up_tip()
        p20.aspirate(12.5, master_mix_water_tubes["A1"])
        p20.dispense(12.5, plate[well])
        p20.drop_tip()
        
        # Add 10.5 ul water
        p20.pick_up_tip()
        p20.aspirate(10.5, master_mix_water_tubes["A2"])
        p20.dispense(10.5, plate[well])
        p20.drop_tip()
        
        # Add 2 ul sample
        p20.pick_up_tip()
        p20.aspirate(2, sample_tubes[well])
        p20.dispense(2, plate[well])
        p20.drop_tip()
        
        # Mix the well
        p20.mix(10, 5, plate[well])
