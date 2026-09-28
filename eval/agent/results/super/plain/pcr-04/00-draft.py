from opentrons import protocol_api

metadata = {"protocolName": "qPCR setup 6 samples triplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    temp_mod = protocol.load_module('temperature module gen2', 1)
    strip_block = temp_mod.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul')
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_2ml_snapcap', 2)
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 4)

    # pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips])

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

    # load liquids into sources
    tube_rack['A1'].load_liquid(master_mix, 500)  # 500 ul master mix
    # samples in strip wells: allocate 200 ul each
    samples = [sample1, sample2, sample3, sample4, sample5, sample6]
    for i, liq in enumerate(samples):
        strip_block.wells()[i].load_liquid(liq, 200)

    # destination wells (first 18)
    dest_wells = plate.wells()[:18]

    # transfer master mix (8 ul each) using same tip
    p300.pick_up_tip()
    for well in dest_wells:
        p300.aspirate(8, tube_rack['A1'])
        p300.dispense(8, well)
    p300.drop_tip()

    # transfer samples (2 ul each) with fresh tip per reaction
    for idx, well in enumerate(dest_wells):
        p300.pick_up_tip()
        src_well = strip_block.wells()[idx]
        p300.aspirate(2, src_well)
        p300.dispense(2, well)
        p300.drop_tip()
