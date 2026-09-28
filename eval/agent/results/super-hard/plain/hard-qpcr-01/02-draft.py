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
    tuberack["A1"].load_liquid(liquid=liquids["sybr"], volume=1000)   # enough for ~100 reactions
    tuberack["A2"].load_liquid(liquid=liquids["fwd 1"], volume=200)
    tuberack["A3"].load_liquid(liquid=liquids["fwd 2"], volume=200)
    tuberack["A4"].load_liquid(liquid=liquids["fwd 3"], volume=200)
    tuberack["B1"].load_liquid(liquid=liquids["rev 1"], volume=200)
    tuberack["B2"].load_liquid(liquid=liquids["rev 2"], volume=200)
    tuberack["B3"].load_liquid(liquid=liquids["rev 3"], volume=200)
    tuberack["B4"].load_liquid(liquid=liquids["water"], volume=1000)
    tuberack["C1"].load_liquid(liquid=liquids["cdna 1"], volume=200)
    tuberack["C2"].load_liquid(liquid=liquids["cdna 2"], volume=200)
    tuberack["C3"].load_liquid(liquid=liquids["cdna 3"], volume=200)
    tuberack["C4"].load_liquid(liquid=liquids["cdna 4"], volume=200)
    tuberack["D1"].load_liquid(liquid=liquids["cdna 5"], volume=200)
    tuberack["D2"].load_liquid(liquid=liquids["cdna 6"], volume=200)
    tuberack["D3"].load_liquid(liquid=liquids["cdna 7"], volume=200)
    tuberack["D4"].load_liquid(liquid=liquids["cdna 8"], volume=200)
    
    def add_reagent(source_well, volume, dest_well):
        """Pick up tip, aspirate volume from source, dispense to dest, drop tip."""
        p20.pick_up_tip()
        p20.aspirate(volume, source_well)
        p20.dispense(volume, dest_well)
        p20.drop_tip()
    
    # helper to get well name column-major
    def well_name(col, row):
        # col 0-11, row 0-7
        return f"{chr(ord('A')+row)}{col+1}"
    
    # mapping gene to primer wells
    fwd_wells = ["A2", "A3", "A4"]
    rev_wells = ["B1", "B2", "B3"]
    cDNA_wells = ["C1","C2","C3","C4","D1","D2","D3","D4"]
    
    well_idx = 0
    for g in range(3):  # genes
        fwd_tube = tuberack[fwd_wells[g]]
        rev_tube = tuberack[rev_wells[g]]
        # samples
        for s in range(8):  # samples
            cdna_tube = tuberack[cDNA_wells[s]]
            for _ in range(3):  # triplicate
                well = well_name(well_idx % 12, well_idx // 12)
                dest = plate[well]
                # SYBR
                add_reagent(tuberack["A1"], 10, dest)
                # forward primer
                add_reagent(fwd_tube, 1, dest)
                # reverse primer
                add_reagent(rev_tube, 1, dest)
                # cDNA
                add_reagent(cdna_tube, 2, dest)
                # water (sample)
                add_reagent(tuberack["B4"], 6, dest)
                well_idx += 1
        # NTCs
        for _ in range(3):
            well = well_name(well_idx % 12, well_idx // 12)
            dest = plate[well]
            # SYBR
            add_reagent(tuberack["A1"], 10, dest)
            # forward primer
            add_reagent(fwd_tube, 1, dest)
            # reverse primer
            add_reagent(rev_tube, 1, dest)
            # no cDNA
            # water (NTC)
            add_reagent(tuberack["B4"], 8, dest)
            well_idx += 1
    
    # Ensure we used exactly 81 wells
    assert well_idx == 81, f"Expected 81 wells, got {well_idx}"
