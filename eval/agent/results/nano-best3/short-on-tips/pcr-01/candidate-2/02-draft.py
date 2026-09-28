from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    sample1 = protocol.define_liquid(name="sample 1", description="DNA sample 1", display_color="#00FF00")
    sample2 = protocol.define_liquid(name="sample 2", description="DNA sample 2", display_color="#0000FF")
    sample3 = protocol.define_liquid(name="sample 3", description="DNA sample 3", display_color="#FFFF00")
    sample4 = protocol.define_liquid(name="sample 4", description="DNA sample 4", display_color="#FF00FF")
    sample5 = protocol.define_liquid(name="sample 5", description="DNA sample 5", display_color="#00FFFF")
    sample6 = protocol.define_liquid(name="sample 6", description="DNA sample 6", display_color="#FFC0CB")
    sample7 = protocol.define_liquid(name="sample 7", description="DNA sample 7", display_color="#800080")
    sample8 = protocol.define_liquid(name="sample 8", description="DNA sample 8", display_color="#808000")
    
    # Load labware
    tip_racks_p300 = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    tip_racks_p20 = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "3")
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", "4")
    
    # Load instruments
    p300_multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tip_racks_p300])
    p20_single = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_racks_p20])
    
    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=master_mix, volume=1000)
    tubes["A2"].load_liquid(liquid=sample1, volume=500)
    tubes["A3"].load_liquid(liquid=sample2, volume=500)
    tubes["A4"].load_liquid(liquid=sample3, volume=500)
    tubes["A5"].load_liquid(liquid=sample4, volume=500)
    tubes["A6"].load_liquid(liquid=sample5, volume=500)
    tubes["B1"].load_liquid(liquid=sample6, volume=500)
    tubes["B2"].load_liquid(liquid=sample7, volume=500)
    tubes["B3"].load_liquid(liquid=sample8, volume=500)
    
    # Define destination wells (first 8 wells of the plate)
    dest_wells = [plate["A1"], plate["A2"], plate["A3"], plate["A4"], plate["A5"], plate["A6"], plate["A7"], plate["A8"]]
    
    # Define sample wells list
    sample_wells = [tubes["A2"], tubes["A3"], tubes["A4"], tubes["A5"], tubes["A6"], tubes["B1"], tubes["B2"], tubes["B3"]]
    
    # Pick up tip for p300_multi and aspirate master mix
    p300_multi.pick_up_tip()
    p300_multi.aspirate(20, tubes["A1"])
    p300_multi.dispense(20, dest_wells)
    p300_multi.drop_tip()
    
    # Pick up tip for p20_single and aspirate samples
    p20_single.pick_up_tip()
    p20_single.aspirate(5, sample_wells)
    p20_single.dispense(5, dest_wells)
    p20_single.drop_tip()
