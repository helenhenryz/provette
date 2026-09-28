# WHAT THIS TESTS (should FIRE, as an error, with the pause sentence)
# 250 ul of medium into each well of a Corning 360 ul plate, a pause that asks for the plate
# to be emptied on the washer, then 250 ul more: 500 ul by the script's arithmetic, over the
# 366 ul the well holds to its rim. The state is right about what the robot poured, and the
# script cannot show what a person does at the pause, so the error stands and its text adds:
# "A pause at line 23 comes before this step; if the plate is emptied by hand or on a washer
# there, the script cannot show it." Four protocols in the public library empty a filter or
# bead plate off the robot this way.
from opentrons import protocol_api

metadata = {"protocolName": "past the rim after a pause", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    wash = protocol.define_liquid("wash", "wash buffer", "#8c564b")
    reservoir["A1"].load_liquid(wash, 10000)
    p300.transfer(250, reservoir["A1"], [plate[f"A{n}"] for n in range(1, 5)], new_tip="once")
    protocol.pause("Empty the plate on the plate washer, then put it back on slot 1")
    p300.transfer(250, reservoir["A1"], [plate[f"A{n}"] for n in range(1, 5)], new_tip="once")
