import json
from opentrons import protocol_api

metadata = {"protocolName": "Seed cell lines", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    tuberack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 3)

    # pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack])

    # define liquids
    line1 = protocol.define_liquid(name='line 1', description='cell line 1', display_color='#FF0000')
    line2 = protocol.define_liquid(name='line 2', description='cell line 2', display_color='#00FF00')
    line3 = protocol.define_liquid(name='line 3', description='cell line 3', display_color='#0000FF')

    # load liquids into tubes (5 ml each)
    tuberack['A1'].load_liquid(liquid=line1, volume=5000)
    tuberack['B1'].load_liquid(liquid=line2, volume=5000)
    tuberack['C1'].load_liquid(liquid=line3, volume=5000)

    # helper to seed a set of columns with a given tube
    def seed_columns(tube_well, start_col, end_col):
        # columns are 1-indexed in plate well names like 'A1'
        p300.pick_up_tip()
        for col in range(start_col, end_col + 1):
            col_str = str(col)
            for row in ['A','B','C','D','E','F','G','H']:
                well = f'{row}{col_str}'
                p300.aspirate(100, tuberack[tube_well])
                p300.dispense(100, plate[well])
                # optional small blow out
                p300.blow_out(plate[well])
        p300.drop_tip()

    # seed line1 in columns 1-4
    seed_columns('A1', 1, 4)
    # seed line2 in columns 5-8
    seed_columns('B1', 5, 8)
    # seed line3 in columns 9-12
    seed_columns('C1', 9, 12)

if __name__ == '__main__':
    # This allows running the file directly for testing (optional)
    from opentrons.simulate import simulate
    protocol = protocol_api.ProtocolContext()
    run(protocol)
