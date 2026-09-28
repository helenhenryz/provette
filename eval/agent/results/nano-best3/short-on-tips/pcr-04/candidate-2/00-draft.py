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
    
    # Pick up tip
    p20_multi.pick_up_tip()
    
    # Define destination wells
    dest_wells = [
        plate["A1"], plate["A2"], plate["A3"],
        plate["A4"], plate["A5"], plate["A6"],
        plate["A7"], plate["A8"], plate["A9"],
        plate["A10"], plate["A11"], plate["A12"],
        plate["B1"], plate["B2"], plate["B3"],
        plate["B4"], plate["B5"], plate["B6"]
    ]
    
    # Distribute master mix (8 ul) to all 18 destination wells in groups
    p20_multi.distribute(8, master_mix_rack["A1"], dest_wells[0:8])
    p20_multi.distribute(8, master_mix_rack["A1"], dest_wells[8:16])
    p20_multi.distribute(8, master_mix_rack["A1"], dest_wells[16:18])
    
    # Map samples to source and destination wells
    samples = [
        (sample_1, block["A1"], dest_wells[0:3]),
        (sample_2, block["A2"], dest_wells[3:6]),
        (sample_3, block["A3"], dest_wells[6:9]),
        (sample_4, block["A4"], dest_wells[9:12]),
        (sample_5, block["A5"], dest_wells[12:15]),
        (sample_6, block["A6"], dest_wells[15:18]),
    ]
    
    # Add 2 ul of each sample to its 3 destination wells
    for sample, source, destinations in samples:
        p20_multi.aspirate(2, source)
        for dest in destinations:
            p20_multi.dispense(2, dest)
    
    # Drop tip
    p20_multi.drop_tip()
