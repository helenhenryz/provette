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
    
    def well_index_to_well(idx):
        col = idx % 12
        row = idx // 12
        return plate[well_name(col, row)]
    
    def well_name(col, row):
        return f"{chr(ord('A')+row)}{col+1}"
    
    def dispense_chunked(src_well, vol_per_well, well_indices):
        """Dispense vol_per_well ul to each well in well_indices using p20, chunking aspirates."""
        i = 0
        n = len(well_indices)
        while i < n:
            max_aspirate = 20
            wells_per_tip = max_aspirate // vol_per_well
            if wells_per_tip == 0:
                wells_per_tip = 1
            take = min(wells_per_tip, n - i)
            volume_needed = take * vol_per_well
            p20.pick_up_tip()
            p20.aspirate(volume_needed, src_well)
            for j in range(take):
                p20.dispense(vol_per_well, well_index_to_well(well_indices[i + j]))
            p20.drop_tip()
            i += take
    
    def mix_well(well, vol, repetitions):
        """Mix the given well by aspirating and dispensing vol ul repetitions times.
        Assumes tip is empty before calling."""
        for _ in range(repetitions):
            p20.aspirate(vol, well)
            p20.dispense(vol, well)
    
    cdna_wells_order = ["C1","C2","C3","C4","D1","D2","D3","D4"]
    
    total_wells_per_gene = 24 + 3  # samples + NTCs
    num_genes = 3
    reps_per_sample = 3
    samples_per_gene = 8
    
    # --- Prepare mix tubes (one tip per mix) ---
    def prepare_mix(dst_tube, fwd_well, rev_well, sybr_vol, fwd_vol, rev_vol, water_vol):
        """Prepare mix in dst_tube using one tip, transferring reagents in chunks."""
        p20.pick_up_tip()
        # sybr
        vol = sybr_vol
        while vol > 0:
            amount = min(20, vol)
            p20.aspirate(amount, tuberack["A1"])
            p20.dispense(amount, dst_tube)
            vol -= amount
        # fwd
        vol = fwd_vol
        while vol > 0:
            amount = min(20, vol)
            p20.aspirate(amount, tuberack[fwd_well])
            p20.dispense(amount, dst_tube)
            vol -= amount
        # rev
        vol = rev_vol
        while vol > 0:
            amount = min(20, vol)
            p20.aspirate(amount, tuberack[rev_well])
            p20.dispense(amount, dst_tube)
            vol -= amount
        # water
        vol = water_vol
        while vol > 0:
            amount = min(20, vol)
            p20.aspirate(amount, tuberack["B4"])
            p20.dispense(amount, dst_tube)
            vol -= amount
        p20.drop_tip()
    
    mix_tubes = {
        "g1_sample": tuberack["A5"],
        "g1_ntc":    tuberack["A6"],
        "g2_sample": tuberack["B5"],
        "g2_ntc":    tuberack["B6"],
        "g3_sample": tuberack["C5"],
        "g3_ntc":    tuberack["C6"],
    }
    
    prepare_mix(mix_tubes["g1_sample"], "A2", "B1", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix(mix_tubes["g1_ntc"],   "A2", "B1", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    prepare_mix(mix_tubes["g2_sample"], "A3", "B2", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix(mix_tubes["g2_ntc"],   "A3", "B2", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    prepare_mix(mix_tubes["g3_sample"], "A4", "B3", sybr_vol=10*24, fwd_vol=1*24, rev_vol=1*24, water_vol=6*24)
    prepare_mix(mix_tubes["g3_ntc"],   "A4", "B3", sybr_vol=10*3,  fwd_vol=1*3,  rev_vol=1*3,  water_vol=8*3)
    
    # --- Dispense mixes to wells (one tip per mix) ---
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
    
    well_idx = 0
    for g in range(num_genes):
        if g == 0:
            sample_tube = mix_tubes["g1_sample"]
            ntc_tube    = mix_tubes["g1_ntc"]
        elif g == 1:
            sample_tube = mix_tubes["g2_sample"]
            ntc_tube    = mix_tubes["g2_ntc"]
        else:
            sample_tube = mix_tubes["g3_sample"]
            ntc_tube    = mix_tubes["g3_ntc"]
        # sample mix
        well_idx = dispense_mix(sample_tube, 18, samples_per_gene * reps_per_sample, well_idx)
        # NTC mix
        well_idx = dispense_mix(ntc_tube, 20, 3, well_idx)
    
    # --- Add cDNA using one tip per sample, mixing after each dispense ---
    for s in range(samples_per_gene):
        cdna_src = tuberack[cdna_wells_order[s]]
        p20.pick_up_tip()
        for g in range(num_genes):
            base = g * total_wells_per_gene
            for r in range(reps_per_sample):
                well_idx_local = base + s * reps_per_sample + r
                well = well_index_to_well(well_idx_local)
                p20.aspirate(2, cdna_src)      # aspirate cDNA for this well
                p20.dispense(2, well)          # dispense into well
                mix_well(well, vol=5, repetitions=3)  # mix after dispensing
        p20.drop_tip()
    
    # final tip drop if any (should be none)
    # assert no tips left? not needed
