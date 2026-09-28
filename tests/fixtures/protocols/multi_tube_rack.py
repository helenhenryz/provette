"""An 8-channel pipette sent to a tube rack, where its tips do not line up with the tubes.

Tubes in a 24-tube rack are about 19 mm apart; the eight tips are 9 mm apart. Sent to tube A1,
tips 1, 3, 5 and 7 go into tubes A1, B1, C1 and D1, and tips 2, 4, 6 and 8 come down between
tubes. Nobody should do this on a real robot, but published protocols do, and the simulator
counts all eight tips as having aspirated. Provette keeps all eight tips in the step: a tip over
no tube is recorded against the tube the protocol named.
"""

metadata = {"protocolName": "8-channel pipette in a tube rack", "apiLevel": "2.13"}


def run(protocol):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300m = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    p300m.pick_up_tip()
    p300m.aspirate(40, rack["A1"])
    p300m.dispense(40, plate["A1"])
    p300m.return_tip()
