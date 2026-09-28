from opentrons import protocol_api

metadata = {"protocolName": "PCR_Assembly", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    temp_module = protocol.load_module("temperature module gen2", 2)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    for i in range(1, 13):
        protocol.define_liquid(name=f"sample {i}", display_color='#1f77b4')
    protocol.define_liquid("polymerase", display_color='#ff7f0e')
    protocol.define_liquid("fwd primer", display_color='#2ca02c')
    protocol.define_liquid("rev primer", display_color='#d62728')
    protocol.define_liquid("water", display_color='#9467bd')
    protocol.define_liquid("buffer", display_color='#8c564b')
    
    # Load liquids into block wells
    sample_names = [f"sample {i}" for i in range(1, 13)]
    for i, name in enumerate(sample_names, start=1):
        if i <= 6:
            well = block[f"A{i}"]
        else:
            well = block[f"B{i-6}"]
        well.load_liquid(liquid=name)
    
    block["C1"].load_liquid(liquid="buffer")
    block["C2"].load_liquid(liquid="polymerase")
    block["C3"].load_liquid(liquid="fwd primer")
    block["C4"].load_liquid(liquid="rev primer")
    block["C5"].load_liquid(liquid="water")
    
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
