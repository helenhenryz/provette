"""A protocol the simulator rejects: it asks a 300 uL pipette to aspirate 500 uL."""

from opentrons import protocol_api

metadata = {"protocolName": "Deliberately wrong"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    p300.pick_up_tip()
    p300.aspirate(500, plate["A1"])  # more than the pipette holds
    p300.drop_tip()
