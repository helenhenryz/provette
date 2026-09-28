# WHAT THIS TESTS (should NOT fire)
# Eight spent samples of 300 ul emptied into one 1.5 ml tube that is never drawn from and
# carries no label at all. A reservoir or tube the robot only ever pours into is a sink, and a
# sink is meant to be filled, whatever it is called.
from opentrons import protocol_api

metadata = {"protocolName": "a sink tube", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    spent = protocol.define_liquid("spent medium", "spent medium", "#7f7f7f")
    for n in range(1, 9):
        plate[f"A{n}"].load_liquid(spent, 1000)
    for n in range(1, 9):
        p300.transfer(300, plate[f"A{n}"], tubes["D6"], new_tip="always")
