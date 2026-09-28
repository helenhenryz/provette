from opentrons import protocol_api

metadata = {"protocolName": "PCR_Assembly", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    temp_module = protocol.load_module("temperature module gen2", 2)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    p20.pick_up_tip()
    
    # Define liquids
    # Define buffer, polymerase, primers, water
    buffer = protocol.define_liquid(name="buffer", description=None)
    polymerase = protocol.define_liquid(name="polymerase", description=None)
    fwd_primer = protocol.define_liquid(name="fwd primer", description=None)
    rev_primer = protocol.define_liquid(name="rev primer", description=None)
    water = protocol.define_liquid(name="water", description=None)
    
    # Define samples
    samples = {}
    for i in range(1, 13):
        samples[i] = protocol.define_liquid(name=f"sample {i}", description=None)
    
    # Load liquids into block wells
    # Load buffer (120 ul)
    block["C1"].load_liquid(liquid=buffer, volume=120)
    # Load polymerase (6 ul)
    block["C2"].load_liquid(liquid=polymerase, volume=6)
    # Load fwd primer (12 ul)
    block["C3"].load_liquid(liquid=fwd_primer, volume=12)
    # Load rev primer (12 ul)
    block["C4"].load_liquid(liquid=rev_primer, volume=12)
    # Load water (126 ul)
    block["C5"].load_liquid(liquid=water, volume=126)
    
    # Load samples (2 ul each)
    for i in range(1, 13):
        if i <= 6:
            well = block[f"A{i}"]
        else:
            well = block[f"B{i-6}"]
        well.load_liquid(liquid=samples[i], volume=2)
    
    # Source wells
    buffer_well = block["C1"]
    polymerase_well = block["C2"]
    fwd_primer_well = block["C3"]
    rev_primer_well = block["C4"]
    water_well = block["C5"]
    
    # Loop over samples
    for i in range(1, 13):
        # Determine sample well
        if i <= 6:
            sample_well = block[f"A{i}"]
        else:
            sample_well = block[f"B{i-6}"]
        
        # Target well in plate
        target_well = plate[f"A{i}"]
        
        # Transfer components
        p20.aspirate(10, buffer_well)
        p20.dispense(10, target_well)
        
        p20.aspirate(0.5, polymerase_well)
        p20.dispense(0.5, target_well)
        
        p20.aspirate(1, fwd_primer_well)
        p20.dispense(1, target_well)
        
        p20.aspirate(1, rev_primer_well)
        p20.dispense(1, target_well)
        
        p20.aspirate(10.5, water_well)
        p20.dispense(10.5, target_well)
        
        p20.aspirate(2, sample_well)
        p20.dispense(2, target_well)
    
    # Drop tip
    p20.drop_tip()
