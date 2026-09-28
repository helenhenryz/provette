from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ==================== LABWARE LOADING ====================
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "1")
    temp_mod = protocol.load_module("temperature module gen2", "2")
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "4")
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # ==================== LIQUID DEFINITIONS ====================
    # Define liquids and capture the returned objects
    sybr_liquid = protocol.define_liquid(name="sybr", description="2x SYBR master mix", display_color="#FF0000")
    fwd_1_liquid = protocol.define_liquid(name="fwd 1", description="Forward primer 1", display_color="#00FF00")
    fwd_2_liquid = protocol.define_liquid(name="fwd 2", description="Forward primer 2", display_color="#00FF00")
    fwd_3_liquid = protocol.define_liquid(name="fwd 3", description="Forward primer 3", display_color="#00FF00")
    rev_1_liquid = protocol.define_liquid(name="rev 1", description="Reverse primer 1", display_color="#00FF00")
    rev_2_liquid = protocol.define_liquid(name="rev 2", description="Reverse primer 2", display_color="#00FF00")
    rev_3_liquid = protocol.define_liquid(name="rev 3", description="Reverse primer 3", display_color="#00FF00")
    cdna_1_liquid = protocol.define_liquid(name="cdna 1", description="cDNA sample 1", display_color="#FFFF00")
    cdna_2_liquid = protocol.define_liquid(name="cdna 2", description="cDNA sample 2", display_color="#FFFF00")
    cdna_3_liquid = protocol.define_liquid(name="cdna 3", description="cDNA sample 3", display_color="#FFFF00")
    cdna_4_liquid = protocol.define_liquid(name="cdna 4", description="cDNA sample 4", display_color="#FFFF00")
    cdna_5_liquid = protocol.define_liquid(name="cdna 5", description="cDNA sample 5", display_color="#FFFF00")
    cdna_6_liquid = protocol.define_liquid(name="cdna 6", description="cDNA sample 6", display_color="#FFFF00")
    cdna_7_liquid = protocol.define_liquid(name="cdna 7", description="cDNA sample 7", display_color="#FFFF00")
    cdna_8_liquid = protocol.define_liquid(name="cdna 8", description="cDNA sample 8", display_color="#FFFF00")
    water_liquid = protocol.define_liquid(name="water", description="Molecular grade water", display_color="#0000FF")
    
    # Mapping of liquid names to block well positions
    liquid_to_well = {
        "sybr": "A1",
        "fwd 1": "A2",
        "fwd 2": "A3",
        "fwd 3": "A4",
        "rev 1": "A5",
        "rev 2": "A6",
        "rev 3": "B1",
        "cdna 1": "B2",
        "cdna 2": "B3",
        "cdna 3": "B4",
        "cdna 4": "B5",
        "cdna 5": "B6",
        "cdna 6": "C1",
        "cdna 7": "C2",
        "cdna 8": "C3",
        "water": "C4"
    }
    
    # Load liquids into block wells with starting volumes
    block.well("A1").load_liquid(liquid=sybr_liquid, volume=1000)
    block.well("A2").load_liquid(liquid=fwd_1_liquid, volume=30)
    block.well("A3").load_liquid(liquid=fwd_2_liquid, volume=30)
    block.well("A4").load_liquid(liquid=fwd_3_liquid, volume=30)
    block.well("A5").load_liquid(liquid=rev_1_liquid, volume=30)
    block.well("A6").load_liquid(liquid=rev_2_liquid, volume=30)
    block.well("B1").load_liquid(liquid=rev_3_liquid, volume=30)
    block.well("B2").load_liquid(liquid=cdna_1_liquid, volume=20)
    block.well("B3").load_liquid(liquid=cdna_2_liquid, volume=20)
    block.well("B4").load_liquid(liquid=cdna_3_liquid, volume=20)
    block.well("B5").load_liquid(liquid=cdna_4_liquid, volume=20)
    block.well("B6").load_liquid(liquid=cdna_5_liquid, volume=20)
    block.well("C1").load_liquid(liquid=cdna_6_liquid, volume=20)
    block.well("C2").load_liquid(liquid=cdna_7_liquid, volume=20)
    block.well("C3").load_liquid(liquid=cdna_8_liquid, volume=20)
    block.well("C4").load_liquid(liquid=water_liquid, volume=1000)
    
    # ==================== HELPER FUNCTION ====================
    def index_to_well(i):
        """Convert 1-based well index to plate well name (column-major order)."""
        zero_based = i - 1
        col = zero_based // 8
        row = zero_based % 8
        col_letter = chr(65 + col)  # 'A', 'B', ...
        return f"{col_letter}{row+1}"
    
    # ==================== MAIN LOOP ====================
    for i in range(1, 82):  # 81 wells total
        plate_well = plate.well(index_to_well(i))
        
        # Calculate well position in the plate map
        block_index = i - 1
        gene = (block_index // 27) + 1  # 1, 2, or 3
        position_in_gene_block = block_index % 27  # 0-26
        is_ntc = position_in_gene_block >= 24  # Last 3 wells per gene are NTC
        
        if not is_ntc:
            sample_index = (position_in_gene_block // 3) + 1  # 1-8
        else:
            sample_index = None
        
        # Determine primer and water volumes
        fwd_liquid_name = f"fwd {gene}"
        rev_liquid_name = f"rev {gene}"
        water_vol = 8 if is_ntc else 6
        cDNA_vol = 2 if not is_ntc else 0
        
        # Get source wells
        sybr_well = block.well(liquid_to_well["sybr"])
        fwd_well = block.well(liquid_to_well[fwd_liquid_name])
        rev_well = block.well(liquid_to_well[rev_liquid_name])
        water_well = block.well(liquid_to_well["water"])
        
        # Perform transfers for this well
        p300.pick_up_tip()
        # 10 ul SYBR master mix
        p300.aspirate(10, sybr_well)
        p300.dispense(10, plate_well)
        # 1 ul forward primer
        p300.aspirate(1, fwd_well)
        p300.dispense(1, plate_well)
        # 1 ul reverse primer
        p300.aspirate(1, rev_well)
        p300.dispense(1, plate_well)
        # cDNA or water for NTC
        if is_ntc:
            p300.aspirate(water_vol, water_well)
            p300.dispense(water_vol, plate_well)
        else:
            # 2 ul cDNA sample
            p300.aspirate(cDNA_vol, block.well(liquid_to_well[f"cdna {sample_index}"]))
            p300.dispense(cDNA_vol, plate_well)
            # 6 ul water
            p300.aspirate(water_vol, water_well)
            p300.dispense(water_vol, plate_well)
        # Drop tip after completing the well
        p300.drop_tip()
