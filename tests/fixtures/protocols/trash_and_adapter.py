"""Steps that name no well: liquid thrown in the trash, and actions done "where the tip is".

Also a plate that sits on an adapter on the heater-shaker, the way a real one does.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Trash, in-place steps, an adapter"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    shaker = protocol.load_module("heaterShakerModuleV1", 1)
    adapter = shaker.load_adapter("opentrons_96_flat_bottom_adapter")
    plate = adapter.load_labware("nest_96_wellplate_200ul_flat")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 9)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    shaker.close_labware_latch()

    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(50, plate["A1"])
    p300.touch_tip()  # no well named: the well the tip is in
    p300.dispense(50, protocol.fixed_trash)  # the rest goes in the trash
    p300.blow_out()  # no place named: still over the trash
    p300.aspirate(30, reservoir["A1"])
    p300.air_gap(20, in_place=True)  # air taken without lifting the tip out
    p300.dispense(50, plate["A2"].top())
    p300.blow_out()  # still at the top of A2
    p300.drop_tip()
