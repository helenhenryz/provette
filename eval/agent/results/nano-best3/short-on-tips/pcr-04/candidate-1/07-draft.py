from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_setup_6samples_triplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip racks
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    
    # Load destination plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    
    # Load source plate for master mix
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    
    # Load temperature module and strip tubes
    temp_mod = protocol.load_module("temperature module gen2", 4)
    strip_tubes = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    
    # Define liquids and keep references
    mm_liquid = protocol.define_liquid(
        name="master mix",
        description="SYBR master mix with primers",
        display_color="#ff0000"
    )
    sample_liquids = {}
    for i in range(1, 7):
        sample_liquids[i] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"cDNA sample {i}",
            display_color="#000000"
        )
    
    # Load master mix into source plate wells A1-H1
    for i in range(8):
        source_plate[f"A{i+1}"].load_liquid(liquid=mm_liquid, volume=30)
    
    # Load samples into strip tubes
    for i in range(1, 7):
        strip_tubes[f"A{i}"].load_liquid(liquid=sample_liquids[i], volume=10)
    
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
    p20_multi.transfer(
        volume=8,
        source=source_plate["A1"],
        destinations=[plate[well] for well in dest_wells[0:8]],
        new_tip="always"
    )
    
    # Master mix distribution - group 2 (next 8 wells)
    p20_multi.transfer(
        volume=8,
        source=source_plate["A1"],
        destinations=[plate[well] for well in dest_wells[8:16]],
        new_tip="always"
    )
    
    # Master mix distribution - group 3 (final 2 wells) using single-channel pipette
    p20_single.transfer(
        volume=8,
        source=source_plate["A1"],
        destinations=[plate[dest_wells[16]], plate[dest_wells[17]]],
        new_tip="always"
    )
    
    # Sample transfers - one tip per sample
    for sample_idx in range(1, 7):
        start = (sample_idx - 1) * 3
        replicate_wells = dest_wells[start:start+3]
        for well in replicate_wells:
            p20_single.transfer(
                volume=2,
                source=strip_tubes[f"A{sample_idx}"],
                destination=plate[well],
                new_tip="always"
            )
