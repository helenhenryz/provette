from opentrons import protocol_api

metadata = {
    'protocolName': 'Pool 25 ul from each of 96 indexed sequencing libraries in a 96-well plate into a single tube',
    'apiLevel': '2.19'
}

def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 1)
    tube_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 2)
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 3)
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips])

    # define liquids and load them into source plate wells
    i = 1
    for well in plate.wells():
        lib = protocol.define_liquid(
            name='library {}'.format(i),
            description='library {}'.format(i),
            display_color=f'#{i:06X}'
        )
        well.load_liquid(
            liquid=lib,
            volume=50
        )
        i += 1

    # pool 25 ul from each well into the first well of the tube rack
    dest_well = tube_rack['A1']
    for well in plate.wells():
        p300.pick_up_tip()
        p300.aspirate(25, well)
        p300.dispense(25, dest_well)
        p300.mix(5, 300, dest_well)
        p300.drop_tip()

    protocol.comment('Pooling complete')
