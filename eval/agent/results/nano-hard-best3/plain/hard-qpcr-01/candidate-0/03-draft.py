from opentrons import protocol_api

metadata = {'protocolName': 'qPCR_setup', 'apiLevel': '2.19'}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    temp_module = protocol.load_module('temperature module gen2', '2')
    block = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '3')
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tip_racks])
    
    # Define liquids
    sybr = protocol.define_liquid(name='sybr', description='2x SYBR master mix', display_color='#FF0000')
    fwd_1 = protocol.define_liquid(name='fwd 1', description='Forward primer 1', display_color='#00FF00')
    fwd_2 = protocol.define_liquid(name='fwd 2', description='Forward primer 2', display_color='#00FF00')
    fwd_3 = protocol.define_liquid(name='fwd 3', description='Forward primer 3', display_color='#00FF00')
    rev_1 = protocol.define_liquid(name='rev 1', description='Reverse primer 1', display_color='#00FF00')
    rev_2 = protocol.define_liquid(name='rev 2', description='Reverse primer 2', display_color='#00FF00')
    rev_3 = protocol.define_liquid(name='rev 3', description='Reverse primer 3', display_color='#00FF00')
    cdna_1 = protocol.define_liquid(name='cdna 1', description='cDNA sample 1', display_color='#FFFF00')
    cdna_2 = protocol.define_liquid(name='cdna 2', description='cDNA sample 2', display_color='#FFFF00')
    cdna_3 = protocol.define_liquid(name='cdna 3', description='cDNA sample 3', display_color='#FFFF00')
    cdna_4 = protocol.define_liquid(name='cdna 4', description='cDNA sample 4', display_color='#FFFF00')
    cdna_5 = protocol.define_liquid(name='cdna 5', description='cDNA sample 5', display_color='#FFFF00')
    cdna_6 = protocol.define_liquid(name='cdna 6', description='cDNA sample 6', display_color='#FFFF00')
    cdna_7 = protocol.define_liquid(name='cdna 7', description='cDNA sample 7', display_color='#FFFF00')
    cdna_8 = protocol.define_liquid(name='cdna 8', description='cDNA sample 8', display_color='#FFFF00')
    water = protocol.define_liquid(name='water', description='Nuclease-free water', display_color='#0000FF')
    
    # Map liquids to source wells on the aluminium block
    source_wells = {
        'sybr': block['A1'],
        'fwd 1': block['A2'],
        'fwd 2': block['A3'],
        'fwd 3': block['A4'],
        'rev 1': block['A5'],
        'rev 2': block['A6'],
        'rev 3': block['B1'],
        'cdna 1': block['B2'],
        'cdna 2': block['B3'],
        'cdna 3': block['B4'],
        'cdna 4': block['B5'],
        'cdna 5': block['B6'],
        'cdna 6': block['C1'],
        'cdna 7': block['C2'],
        'cdna 8': block['C3'],
        'water': block['C4']
    }
    
    # Load liquids into source wells with realistic starting volumes
    source_wells['sybr'].load_liquid(liquid=sybr, volume=1000)
    source_wells['fwd 1'].load_liquid(liquid=fwd_1, volume=100)
    source_wells['fwd 2'].load_liquid(liquid=fwd_2, volume=100)
    source_wells['fwd 3'].load_liquid(liquid=fwd_3, volume=100)
    source_wells['rev 1'].load_liquid(liquid=rev_1, volume=100)
    source_wells['rev 2'].load_liquid(liquid=rev_2, volume=100)
    source_wells['rev 3'].load_liquid(liquid=rev_3, volume=100)
    source_wells['cdna 1'].load_liquid(liquid=cdna_1, volume=50)
    source_wells['cdna 2'].load_liquid(liquid=cdna_2, volume=50)
    source_wells['cdna 3'].load_liquid(liquid=cdna_3, volume=50)
    source_wells['cdna 4'].load_liquid(liquid=cdna_4, volume=50)
    source_wells['cdna 5'].load_liquid(liquid=cdna_5, volume=50)
    source_wells['cdna 6'].load_liquid(liquid=cdna_6, volume=50)
    source_wells['cdna 7'].load_liquid(liquid=cdna_7, volume=50)
    source_wells['cdna 8'].load_liquid(liquid=cdna_8, volume=50)
    source_wells['water'].load_liquid(liquid=water, volume=1000)
    
    # Set temperature module to 4°C for cold block
    temp_module.set_temperature(4)
    
    # Generate list of compositions in the order expected by the platemap
    genes = ['1', '2', '3']
    fwd_primes = ['fwd 1', 'fwd 2', 'fwd 3']
    rev_primes = ['rev 1', 'rev 2', 'rev 3']
    cdna_samples = [f'cdna {i}' for i in range(1, 9)]  # cdna 1 to cdna 8
    
    compositions = []
    for gene_idx, gene in enumerate(genes):
        fwd = fwd_primes[gene_idx]
        rev = rev_primes[gene_idx]
        for rep in range(3):
            for cdna in cdna_samples:
                compositions.append({
                    'sybr': 10,
                    'fwd': fwd,
                    'rev': rev,
                    'cdna': cdna,
                    'water': 6,
                    'type': 'cDNA'
                })
        for rep in range(3):
            compositions.append({
                'sybr': 10,
                'fwd': fwd,
                'rev': rev,
                'cdna': None,
                'water': 8,
                'type': 'NTC'
            })
    
    # Get ordered list of plate wells (row-major order)
    plate_wells = list(plate.wells())
    
    # Perform transfers for each composition
    for composition, target_well in zip(compositions, plate_wells):
        # sybr
        vol_sybr = composition['sybr']
        p20.pick_up_tip()
        p20.aspirate(vol_sybr, source_wells['sybr'])
        p20.dispense(vol_sybr, target_well)
        p20.drop_tip()
        
        # forward primer (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, source_wells[composition['fwd']])
        p20.dispense(1, target_well)
        p20.drop_tip()
        
        # reverse primer (1 ul)
        p20.pick_up_tip()
        p20.aspirate(1, source_wells[composition['rev']])
        p20.dispense(1, target_well)
        p20.drop_tip()
        
        # cDNA (2 ul) if not NTC
        if composition['cdna'] is not None:
            p20.pick_up_tip()
            p20.aspirate(2, source_wells[composition['cdna']])
            p20.dispense(2, target_well)
            p20.drop_tip()
        
        # water to reach 20 ul total
        vol_water = composition['water']
        p20.pick_up_tip()
        p20.aspirate(vol_water, source_wells['water'])
        p20.dispense(vol_water, target_well)
        p20.drop_tip()
