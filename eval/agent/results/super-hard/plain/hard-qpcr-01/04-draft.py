import math

metadata = {"protocolName": "qPCR setup 8 samples 3 genes triplicate", "apiLevel": "2.19"}

def run(protocol):
    # labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # define liquids
    liquids = {
        "sybr": protocol.define_liquid(name="sybr", description="2x SYBR master mix", display_color="#FF0000"),
        "fwd 1": protocol.define_liquid(name="fwd 1", description="forward primer gene 1", display_color="#00FF00"),
        "fwd 2": protocol.define_liquid(name="fwd 2", description="forward primer gene 2", display_color="#00FFFF"),
        "fwd 3": protocol.define_liquid(name="fwd 3", description="forward primer gene 3", display_color="#FF00FF"),
        "rev 1": protocol.define_liquid(name="rev 1", description="reverse primer gene 1", display_color="#0000FF"),
        "rev 2": protocol.define_liquid(name="rev 2", description="reverse primer gene 2", display_color="#FFA500"),
        "rev 3": protocol.define_liquid(name="rev 3", description="reverse primer gene 3", display_color="#800080"),
        "cdna 1": protocol.define_liquid(name="cdna 1", description="cDNA sample 1", display_color="#008000"),
        "cdna 2": protocol.define_liquid(name="cdna 2", description="cDNA sample 2", display_color="#008080"),
        "cdna 3": protocol.define_liquid(name="cdna 3", description="cDNA sample 3", display_color="#800000"),
        "cdna 4": protocol.define_liquid(name="cdna 4", description="cDNA sample 4", display_color="#808000"),
        "cdna 5": protocol.define_liquid(name="cdna 5", description="cDNA sample 5", display_color="#800080"),
        "cdna 6": protocol.define_liquid(name="cdna 6", description="cDNA sample 6", display_color="#000080"),
        "cdna 7": protocol.define_liquid(name="cdna 7", description="cDNA sample 7", display_color="#008080"),
        "cdna 8": protocol.define_liquid(name="cdna 8", description="cDNA sample 8", display_color="#808080"),
        "water": protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF"),
    }
    
    # initial volumes (ul) in source tubes
    tuberack["A1"].load_liquid(liquid=liquids["sybr"], volume=1500)   # plenty
    tuberack["A2"].load_liquid(liquid=liquids["fwd 1"], volume=500)
    tuberack["A3"].load_liquid(liquid=liquids["fwd 2"], volume=500)
    tuberack["A4"].load_liquid(liquid=liquids["fwd 3"], volume=500)
    tuberack["B1"].load_liquid(liquid=liquids["rev 1"], volume=500)
    tuberack["B2"].load_liquid(liquid=liquids["rev 2"], volume=500)
    tuberack["B3"].load_liquid(liquid=liquids["rev 3"], volume=500)
    tuberack["B4"].load_liquid(liquid=liquids["water"], volume=1500)
    tuberack["C1"].load_liquid(liquid=liquids["cdna 1"], volume=200)
    tuberack["C2"].load_liquid(liquid=liquids["cdna 2"], volume=200)
    tuberack["C3"].load_liquid(liquid=liquids["cdna 3"], volume=200)
    tuberack["C4"].load_liquid(liquid=liquids["cdna 4"], volume=200)
    tuberack["D1"].load_liquid(liquid=liquids["cdna 5"], volume=200)
    tuberack["D2"].load_liquid(liquid=liquids["cdna 6"], volume=200)
    tuberack["D3"].load_liquid(liquid=liquids["cdna 7"], volume=200)
    tuberack["D4"].load_liquid(liquid=liquids["cdna 8"], volume=200)
    
    # mix tubes (empty initially) - using columns 5 and 6
    mix_tubes = {
        "g1_sample": tuberack["A5"],
        "g1_ntc":    tuberack["A6"],
        "g2_sample": tuberack["B5"],
        "g2_ntc":    tuberack["B6"],
        "g3_sample": tuberack["C5"],
        "g3_ntc":    tuberack["C6"],
    }
    
    # helper to prepare a mix for a gene
    def prepare_mix_gene(dest_tube, fwd_well, rev_well, sybr_vol, fwd_vol, rev_vol, water_vol):
        p20.pick_up_tip()
        p20.aspirate(sybr_vol, tuberack["A1"])
        p20.dispense(sybr_vol, dest_tube)
        p20.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(fwd_vol, tuberack[fwd_well])
        p20.dispense(fwd_vol, dest_tube)
        p20.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(rev_vol, tuberack[rev_well])
        p20.dispense(rev_vol, dest_tube)
        p20.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(water_vol, tuberack["B4"])
        p20.dispense(water_vol, dest_tube)
        p20.drop_tip()
    
    # prepare mixes per gene
    # Gene 1
    prepare_mix_gene(mix_tubes["g1_sample"], "A2", "B1", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix_gene(mix_tubes["g1_ntc"],   "A2", "B1", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    # Gene 2
    prepare_mix_gene(mix_tubes["g2_sample"], "A3", "B2", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix_gene(mix_tubes["g2_ntc"],   "A3", "B2", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    # Gene 3
    prepare_mix_gene(mix_tubes["g3_sample"], "A4", "B3", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix_gene(mix_tubes["g3_ntc"],   "A4", "B3", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    
    # helper to dispense mix from a tube to multiple wells
    def dispense_mix(source_tube, aliquot, num_wells, start_well_idx):
        total = aliquot * num_wells
        p20.pick_up_tip()
        p20.aspirate(total, source_tube)
        for i in range(num_wells):
            well_idx = start_well_idx + i
            well = well_name(well_idx % 12, well_idx // 12)
            dest = plate[well]
            p20.dispense(aliquot, dest)
        p20.drop_tip()
        return start_well_idx + num_wells
    
    # helper to add cDNA to sample wells (fresh tip per well)
    def add_cdna(cdna_tube, start_well_idx, num_wells):
        for i in range(num_wells):
            well_idx = start_well_idx + i
            well = well_name(well_idx % 12, well_idx // 12)
            dest = plate[well]
            p20.pick_up_tip()
            p20.aspirate(2, cdna_tube)
            p20.dispense(2, dest)
            p20.drop_tip()
        return start_well_idx + num_wells
    
    # well_name function
    def well_name(col, row):
        return f"{chr(ord('A')+row)}{col+1}"
    
    # Process genes
    well_idx = 0
    cdna_wells = ["C1","C2","C3","C4","D1","D2","D3","D4"]
    for g in range(3):
        if g == 0:
            sample_tube = mix_tubes["g1_sample"]
            ntc_tube    = mix_tubes["g1_ntc"]
            fwd_well    = "A2"
            rev_well    = "B1"
        elif g == 1:
            sample_tube = mix_tubes["g2_sample"]
            ntc_tube    = mix_tubes["g2_ntc"]
            fwd_well    = "A3"
            rev_well    = "B2"
        else:
            sample_tube = mix_tubes["g3_sample"]
            ntc_tube    = mix_tubes["g3_ntc"]
            fwd_well    = "A4"
            rev_well    = "B3"
        # samples: 8 samples *3 replicates =24 wells
        well_idx = dispense_mix(sample_tube, 18, 24, well_idx)
        # add cDNA to those 24 wells
        cDNA_start_idx = well_idx - 24  # start of sample wells for this gene
        for s in range(8):
            cdna_tube = tuberack[cdna_wells[s]]
            for _ in range(3):
                p20.pick_up_tip()
                p20.aspirate(2, cdna_tube)
                p20.dispense(2, plate[well_name((cDNA_start_idx) % 12, cDNA_start_idx // 12)])
                p20.drop_tip()
                cDNA_start_idx += 1
        # NTCs: 3 wells
        well_idx = dispense_mix(ntc_tube, 20, 3, well_idx)
    # final check
    assert well_idx == 81, f"Expected 81 wells, got {well_idx}"
