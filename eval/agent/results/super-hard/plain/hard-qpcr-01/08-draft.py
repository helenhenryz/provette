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
        idx = 0
        n = len(well_indices)
        while idx < n:
            # how many wells we can serve with one tip
            max_aspirate = 20
            wells_per_tip = max_aspirate // vol_per_well
            if wells_per_tip == 0:
                wells_per_tip = 1
            take = min(wells_per_tip, n - idx)
            volume_needed = take * vol_per_well
            p20.pick_up_tip()
            p20.aspirate(volume_needed, src_well)
            for j in range(take):
                p20.dispense(vol_per_well, well_index_to_well(well_indices[idx + j]))
            p20.drop_tip()
            idx += take
    
    cdna_wells_order = ["C1","C2","C3","C4","D1","D2","D3","D4"]
    
    total_wells_per_gene = 24 + 3  # samples + NTCs
    for g in range(3):
        base = g * total_wells_per_gene
        sample_indices = [base + i for i in range(24)]  # first 24 are samples
        ntc_indices    = [base + 24 + i for i in range(3)]  # last 3 are NTCs
        
        # SYBR 10 ul to all 27 wells
        dispense_chunked(tuberack["A1"], 10, sample_indices + ntc_indices)
        # fwd primer
        fwd_src = tuberack[["A2","A3","A4"][g]]
        dispense_chunked(fwd_src, 1, sample_indices + ntc_indices)
        # rev primer
        rev_src = tuberack[["B1","B2","B3"][g]]
        dispense_chunked(rev_src, 1, sample_indices + ntc_indices)
        # water: 6 ul to all, then extra 2 ul to NTCs
        dispense_chunked(tuberack["B4"], 6, sample_indices + ntc_indices)
        dispense_chunked(tuberack["B4"], 2, ntc_indices)
        # cDNA: one tip per sample, dispense to its 3 replicates within this gene
        for s in range(8):
            cdna_src = tuberack[cdna_wells_order[s]]
            p20.pick_up_tip()
            for r in range(3):
                well_idx_local = sample_indices[s*3 + r]  # within sample block
                p20.dispense(2, well_index_to_well(well_idx_local))
            p20.drop_tip()
    
    # final tip drop if any (should be none)
    # assert no tips left? not needed
