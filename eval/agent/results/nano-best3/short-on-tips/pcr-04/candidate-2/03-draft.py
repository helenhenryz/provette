from opentrons import protocol_api

metadata = {"protocolName": "qPCR_setup_6samples_triplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    master_mix_rack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 2)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    module = protocol.load_module("temperature module gen2", 4)
    block = module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="SYBR green master mix with primers", display_color="#FF0000")
    sample_1 = protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    sample_2 = protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    sample_3 = protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    sample_4 = protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    sample_5 = protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    sample_6 = protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#FFFFFF")
    
    # Load liquids into source wells
    master_mix_rack["A1"].load_liquid(liquid=master_mix, volume=1000)
    block["A1"].load_liquid(liquid=sample_1, volume=100)
    block["A2"].load_liquid(liquid=sample_2, volume=100)
    block["A3"].load_liquid(liquid=sample_3, volume=100)
    block["A4"].load_liquid(liquid=sample_4, volume=100)
    block["A5"].load_liquid(liquid=sample_5, volume=100)
    block["A6"].load_liquid(liquid=sample_6, volume=100)
    
    # Load pipette
    p20_multi = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tip_rack])
    
    # Define destination wells (18 wells total)
    dest_wells = [
        plate["A1"], plate["A2"], plate["A3"], plate["A4"], plate["A5"], plate["A6"],
        plate["A7"], plate["A8"], plate["A9"], plate["A10"], plate["A11"], plate["A12"],
        plate["B1"], plate["B2"], plate["B3"], plate["B4"], plate["B5"], plate["B6"]
    ]
    
    # Fill each destination well with 8 ul of master mix
    for well in dest_wells:
        p20_multi.aspirate(8, master_mix_rack["A1"])
        p20_multi.dispense(8, well)
    
    # Add 2 ul of each sample to its 3 destination wells
    # Map each sample to a consecutive group of 3 wells in dest_wells
    sample_sources = [
        block["A1"],  # sample 1
        block["A2"],  # sample 2
        block["A3"],  # sample 3
        block["A4"],  # sample 4
        block["A5"],  # sample 5
        block["A6"],  # sample 6
    ]
    
    for i, source in enumerate(sample_sources):
        dest_group = dest_wells[i*3 : i*3+3]
        for dest in dest_group:
            p20_multi.aspirate(2, source)
            p20_multi.dispense(2, dest)
    
    # Drop tip
    p20_multi.drop_tip()
