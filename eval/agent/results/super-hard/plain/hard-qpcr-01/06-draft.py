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
    
    def transfer_chunks(src, dst, vol, chunk=20):
        """Transfer vol from src to dst using p20, in chunks of chunk ul."""
        while vol > 0:
            amount = min(chunk, vol)
            p20.pick_up_tip()
            p20.aspirate(amount, src)
            p20.dispense(amount, dst)
            p20.drop_tip()
            vol -= amount
    
    # helper to prepare a mix for a gene using chunked transfers
    def prepare_mix_gene(dest_tube, fwd_well, rev_well, sybr_vol, fwd_vol, rev_vol, water_vol):
        # sybr
        transfer_chunks(tuberack["A1"], dest_tube, sybr_vol)
        # fwd
        transfer_chunks(tuberack[fwd_well], dest_tube, fwd_vol)
        # rev
        transfer_chunks(tuberack[rev_well], dest_tube, rev_vol)
        # water
        transfer_chunks(tuberack["B4"], dest_tube, water_vol)
    
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
    
    # helper to dispense mix from a tube to multiple wells using chunked aspiration
    def dispense_mix_chunked(source_tube, aliquot, num_wells, start_well_idx):
        """Dispense aliquot to num_wells wells starting at start_well_idx.
        Aspirates in chunks to fit tip size."""
        wells_done = 0
        while wells_done < num_wells:
            # determine how many wells we can fill with one tip load
            max_aspirate = 20  # p20 max
            # max wells per aspirate = floor(max_aspirate / aliquot)
            wells_per_tip = max_aspirate // aliquot
            if wells_per_tip == 0:
                wells_per_tip = 1  # should not happen as aliquot <=20
            to_do = min(wells_per_tip, num_wells - wells_done)
            volume_needed = to_do * aliquot
            p20.pick_up_tip()
            p20.aspirate(volume_needed, source_tube)
            for i in range(to_do):
                well_idx = start_well_idx + wells_done + i
                well = well_name(well_idx % 12, well_idx // 12)
                dest = plate[well]
                p20.dispense(aliquot, dest)
            p20.drop_tip()
            wells_done += to_do
        return start_well_idx + num_wells
    
    # well_name function
    def well_name(col, row):
        return f"{chr(ord('A')+row)}{col+1}"
    
    # Process genes
    well_idx = 0
    num_genes = 3
    reps_per_sample = 3
    samples_per_gene = 8
    
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
        # dispense sample mix to samples (8 samples *3 reps =24 wells)
        well_idx = dispense_mix_chunked(sample_tube, 18, samples_per_gene * reps_per_sample, well_idx)
        # dispense NTC mix to 3 wells
        well_idx = dispense_mix_chunked(ntc_tube, 20, 3, well_idx)
        # add cDNA to the sample wells of this gene using one tip per sample
        base_idx = well_idx - (samples_per_gene * reps_per_sample)  # start of sample wells for this gene
        for s in range(samples_per_gene):
            cdna_tube = tuberack[cdna_wells[s]]
            p20.pick_up_tip()
            for r in range(reps_per_sample):
                target_idx = base_idx + s * reps_per_sample + r
                well = well_name(target_idx % 12, target_idx // 12)
                dest = plate[well]
                p20.dispense(2, dest)
            p20.drop_tip()
    
    # final check
    assert well_idx == 81, f"Expected 81 wells, got {well_idx}"
