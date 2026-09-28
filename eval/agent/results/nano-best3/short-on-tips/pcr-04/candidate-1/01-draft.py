from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_setup_6samples_triplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip racks
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    
    # Load plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    
    # Load tube rack for master mix
    master_mix_tubes = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 3)
    
    # Load temperature module and strip tubes
    temp_mod = protocol.load_module("temperature module gen2", 4)
    strip_tubes = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Define liquids
    protocol.define_liquid(
        name="master mix",
        description="SYBR master mix with primers",
        display_color="#ff0000"
    )
    protocol.define_liquid(
        name="sample 1",
        description="cDNA sample 1",
        display_color="#00ff00"
    )
    protocol.define_liquid(
        name="sample 2",
        description="cDNA sample 2",
        display_color="#0000ff"
    )
    protocol.define_liquid(
        name="sample 3",
        description="cDNA sample 3",
        display_color="#ffff00"
    )
    protocol.define_liquid(
        name="sample 4",
        description="cDNA sample 4",
        display_color="#ff00ff"
    )
    protocol.define_liquid(
        name="sample 5",
        description="cDNA sample 5",
        display_color="#00ffff"
    )
    protocol.define_liquid(
        name="sample 6",
        description="cDNA sample 6",
        display_color="#808080"
    )
    
    # Load liquids into source wells
    # Master mix
    master_mix_tube = master_mix_tubes["A1"]
    master_mix_tube.load_liquid(liquid="master mix", volume=200)
    
    # Samples
    for i in range(1, 7):
        strip_tubes[f"A{i}"].load_liquid(liquid=f"sample {i}", volume=10)
    
    # Load pipettes
    p20_multi = protocol.load_instrument("p20_multi_gen2", "left", tip_racks=[tip_racks])
    p20_single = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Destination wells in column-major order (18 wells)
    dest_wells = [
        "A1", "B1", "C1", "D1", "E1", "F1", "G1", "H1",
        "A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2",
        "A3", "B3"
    ]
    
    # Master mix distribution - group 1 (first 8 wells)
    p20_multi.pick_up_tip()
    p20_multi.aspirate(8, master_mix_tube)
    p20_multi.dispense(8, [plate[well] for well in dest_wells[0:8]])
    p20_multi.drop_tip()
    
    # Master mix distribution - group 2 (next 8 wells)
    p20_multi.pick_up_tip()
    p20_multi.aspirate(8, master_mix_tube)
    p20_multi.dispense(8, [plate[well] for well in dest_wells[8:16]])
    p20_multi.drop_tip()
    
    # Master mix distribution - group 3 (final 2 wells) using single-channel pipette
    p20_single.pick_up_tip()
    p20_single.aspirate(8, master_mix_tube)
    for well in dest_wells[16:18]:
        p20_single.dispense(8, plate[well])
    p20_single.drop_tip()
    
    # Sample transfers - one tip per sample
    for sample_idx in range(1, 7):
        start = (sample_idx - 1) * 3
        replicate_wells = dest_wells[start:start+3]
        p20_single.pick_up_tip()
        p20_single.aspirate(6, strip_tubes[f"A{sample_idx}"])
        for well in replicate_wells:
            p20_single.dispense(2, plate[well])
        p20_single.drop_tip()
