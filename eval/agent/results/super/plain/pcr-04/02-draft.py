from opentrons import protocol_api

metadata = {"protocolName": "qPCR setup 6 samples triplicate with NTC", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    temp_mod = protocol.load_module('temperature module gen2', 1)
    strip_block = temp_mod.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_2ml_snapcap', 2)
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)
    tips_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 4)

    # pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tips_20])

    # define liquids
    master_mix = protocol.define_liquid(
        name='master mix',
        description='SYBR master mix with primers',
        display_color='#FF0000'
    )
    sample1 = protocol.define_liquid(
        name='sample 1',
        description='cDNA sample 1',
        display_color='#00FF00'
    )
    sample2 = protocol.define_liquid(
        name='sample 2',
        description='cDNA sample 2',
        display_color='#0000FF'
    )
    sample3 = protocol.define_liquid(
        name='sample 3',
        description='cDNA sample 3',
        display_color='#FFA500'
    )
    sample4 = protocol.define_liquid(
        name='sample 4',
        description='cDNA sample 4',
        display_color='#800080'
    )
    sample5 = protocol.define_liquid(
        name='sample 5',
        description='cDNA sample 5',
        display_color='#00FFFF'
    )
    sample6 = protocol.define_liquid(
        name='sample 6',
        description='cDNA sample 6',
        display_color='#FFFF00'
    )
    water = protocol.define_liquid(
        name='water',
        description='nuclease-free water',
        display_color='#FFFFFF'
    )

    # load liquids into sources
    tube_rack['A1'].load_liquid(master_mix, 500)  # 500 ul master mix
    # samples in strip wells: allocate 200 ul each
    samples = [sample1, sample2, sample3, sample4, sample5, sample6]
    for i, liq in enumerate(samples):
        strip_block.wells()[i].load_liquid(liq, 200)
    # water for NTC: place in tube rack B1
    tube_rack['B1'].load_liquid(water, 200)

    # set temperature block to 4°C
    temp_mod.set_temperature(4)
    # destination wells in column order: A1,B1,C1...,H1,A2,B2...
    rows = ['A','B','C','D','E','F','G','H']
    dest_wells = []
    for col in range(1, 13):  # 1 to 12
        for r in rows:
            dest_wells.append(plate[f'{r}{col}'])
    # we need 18 sample wells + 3 NTC wells = 21 wells
    dest_wells = dest_wells[:21]

    # transfer master mix (8 ul each) using same tip
    p20.pick_up_tip()
    for well in dest_wells:
        p20.aspirate(8, tube_rack['A1'])
        p20.dispense(8, well)
    p20.drop_tip()

    # transfer samples (2 ul each) with fresh tip per reaction and mix
    for idx in range(18):  # first 18 wells are samples
        well = dest_wells[idx]
        p20.pick_up_tip()
        # determine which sample: each sample appears in 3 consecutive wells
        sample_idx = idx // 3  # 0-5
        src_well = strip_block.wells()[sample_idx]
        p20.aspirate(2, src_well)
        p20.dispense(2, well)
        # mix 5 times with 8 ul volume (80% of 10 ul)
        p20.mix(5, 8, well)
        p20.drop_tip()

    # transfer NTC (2 ul water) for last 3 wells
    for idx in range(18, 21):
        well = dest_wells[idx]
        p20.pick_up_tip()
        p20.aspirate(2, tube_rack['B1'])  # water
        p20.dispense(2, well)
        p20.mix(5, 8, well)
        p20.drop_tip()

    # deactivate temperature module
    temp_mod.deactivate()
