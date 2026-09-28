from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_setup_6samples_triplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    master_mix_tuberack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    temp_module = protocol.load_module("temperature module gen2", 4)
    cDNA_block = temp_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    protocol.define_liquid(name="master mix", description="SYBR master mix with primers", display_color="#FF0000")
    protocol.define_liquid(name="sample 1", description="cDNA sample 1", display_color="#00FF00")
    protocol.define_liquid(name="sample 2", description="cDNA sample 2", display_color="#0000FF")
    protocol.define_liquid(name="sample 3", description="cDNA sample 3", display_color="#FFFF00")
    protocol.define_liquid(name="sample 4", description="cDNA sample 4", display_color="#FF00FF")
    protocol.define_liquid(name="sample 5", description="cDNA sample 5", display_color="#00FFFF")
    protocol.define_liquid(name="sample 6", description="cDNA sample 6", display_color="#800080")
    
    master_mix_tuberack["A1"].load_liquid(liquid="master mix", volume=1000)
    cDNA_block["A1"].load_liquid(liquid="sample 1", volume=1000)
    cDNA_block["A2"].load_liquid(liquid="sample 2", volume=1000)
    cDNA_block["A3"].load_liquid(liquid="sample 3", volume=1000)
    cDNA_block["A4"].load_liquid(liquid="sample 4", volume=1000)
    cDNA_block["A5"].load_liquid(liquid="sample 5", volume=1000)
    cDNA_block["A6"].load_liquid(liquid="sample 6", volume=1000)
    
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    dest_wells = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4","B5","B6"]
    
    for i, well in enumerate(dest_wells):
        sample_num = (i // 3) + 1
        
        p20.pick_up_tip()
        p20.aspirate(8, master_mix_tuberack["A1"])
        p20.dispense(8, plate[well])
        sample_source = cDNA_block["A"+str(sample_num)]
        p20.aspirate(2, sample_source)
        p20.dispense(2, plate[well])
        p20.drop_tip()
