from opentrons import protocol_api

metadata = {'protocolName': 'Cherrypick 10ul transfers', 'apiLevel': '2.19'}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 1)
    dest_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    tip_rack = protocol.load_labware('opentrons_96_tiprack_20ul', 3)

    # Load pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tip_rack])

    # Define liquids with description and capture the returned liquid object
    b3_liquid = protocol.define_liquid(name='B3', description='', display_color='#1f77b4')
    c7_liquid = protocol.define_liquid(name='C7', description='', display_color='#ff7f0e')
    d1_liquid = protocol.define_liquid(name='D1', description='', display_color='#2ca02c')
    a12_liquid = protocol.define_liquid(name='A12', description='', display_color='#d62728')
    h6_liquid = protocol.define_liquid(name='H6', description='', display_color='#9467bd')
    e5_liquid = protocol.define_liquid(name='E5', description='', display_color='#8c564b')
    f9_liquid = protocol.define_liquid(name='F9', description='', display_color='#e377c2')
    g2_liquid = protocol.define_liquid(name='G2', description='', display_color='#17becf')
    b11_liquid = protocol.define_liquid(name='B11', description='', display_color='#1f77b4')
    c4_liquid = protocol.define_liquid(name='C4', description='', display_color='#ff7f0e')

    # Load liquids into source wells
    source_plate['B3'].load_liquid(liquid=b3_liquid, volume=150)
    source_plate['C7'].load_liquid(liquid=c7_liquid, volume=150)
    source_plate['D1'].load_liquid(liquid=d1_liquid, volume=150)
    source_plate['A12'].load_liquid(liquid=a12_liquid, volume=150)
    source_plate['H6'].load_liquid(liquid=h6_liquid, volume=150)
    source_plate['E5'].load_liquid(liquid=e5_liquid, volume=150)
    source_plate['F9'].load_liquid(liquid=f9_liquid, volume=150)
    source_plate['G2'].load_liquid(liquid=g2_liquid, volume=150)
    source_plate['B11'].load_liquid(liquid=b11_liquid, volume=150)
    source_plate['C4'].load_liquid(liquid=c4_liquid, volume=150)

    # Cherrypick transfers
    transfers = [
        ('B3', 'A1'),
        ('C7', 'B1'),
        ('D1', 'C1'),
        ('A12', 'D1'),
        ('H6', 'E1'),
        ('E5', 'F1'),
        ('F9', 'G1'),
        ('G2', 'H1'),
        ('B11', 'A2'),
        ('C4', 'B2')
    ]

    for source, dest in transfers:
        p20.pick_up_tip()
        p20.aspirate(10, source_plate[source])
        p20.dispense(10, dest_plate[dest])
        p20.drop_tip()
