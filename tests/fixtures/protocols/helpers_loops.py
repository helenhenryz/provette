"""A protocol written with helper functions and loops.

Most real protocols are written like this. Provette must still say which line of the file caused
each step: the line inside the helper, and the chain of calls that led to it.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Helpers and loops"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def add_and_mix(pipette, volume, source, dest):
    pipette.aspirate(volume, source)
    pipette.dispense(volume, dest)
    pipette.mix(2, volume, dest)


def with_fresh_tip(pipette, action, *args):
    pipette.pick_up_tip()
    action(pipette, *args)
    pipette.drop_tip()


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    for column in (1, 2):
        with_fresh_tip(p300, add_and_mix, 50, rack["A1"], plate[f"A{column}"])
