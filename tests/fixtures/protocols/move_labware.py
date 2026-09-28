"""A plate is moved by hand in the middle of the run, and liquids are declared three ways."""

from opentrons import protocol_api

metadata = {"protocolName": "Move a plate; declare liquids"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    water = protocol.define_liquid("water", description="nuclease-free water", display_color="#00FFFF")
    reservoir["A1"].load_liquid(water, 8000)  # one well
    plate.load_liquid(["A1", "A2"], 20, water)  # several wells, the same volume
    plate.load_liquid_by_well({"B1": 10, "B2": 15}, water)  # several wells, different volumes
    plate.load_empty(["C1"])  # "this well starts empty"

    p300.pick_up_tip()
    p300.aspirate(50, reservoir["A1"])
    p300.dispense(50, plate["C1"])

    protocol.move_labware(plate, 5)  # a person carries the plate from slot 1 to slot 5

    p300.aspirate(30, plate["C1"])  # the same plate, the same well, a new place
    p300.dispense(30, plate["A1"])
    p300.drop_tip()
