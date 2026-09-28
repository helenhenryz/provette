import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Fill LB and inoculate glycerol stocks", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    lb_res = protocol.load_labware('nest_1_reservoir_195ml', 1)
    dest_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 2)
    src_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 3)
    tiprack_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', 4)
    tiprack_20 = protocol.load_labware('opentrons_96_tiprack_20ul', 5)

    # pipettes
    p1000 = protocol.load_instrument('p1000_single_gen2', 'right', tip_racks=[tiprack_1000])
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack_20])

    # liquids
    lb = protocol.define_liquid(name='lb', description='LB medium', display_color='#00FF00')
    glycerol = protocol.define_liquid(name='glycerol_stock', description='Glycerol stocks', display_color='#FFA500')

    # load liquids
    lb_res['A1'].load_liquid(liquid=lb, volume=195000)  # ~195 mL enough
    for well in src_plate.wells():
        well.load_liquid(liquid=glycerol, volume=200)  # realistic volume for 200ul plate

    # fill LB 500 ul per well
    for well in dest_plate.wells():
        p1000.pick_up_tip()
        p1000.aspirate(500, lb_res['A1'])
        p1000.dispense(500, well)
        p1000.drop_tip()

    # inoculate 5 ul from matching well (no mixing needed)
    for src_well, dst_well in zip(src_plate.wells(), dest_plate.wells()):
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, dst_well)
        p20.drop_tip()
