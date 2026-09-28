# WHAT THIS TESTS (should NOT fire)
# An 8-channel p300 distributing 150 ul to a plate: every volume is well inside its range. Old
# API level, no liquids declared, so the rule must not depend on either.
from opentrons import protocol_api

metadata = {"protocolName": "multi-channel in range", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    m300.pick_up_tip()
    for n in range(1, 13):
        m300.aspirate(150, reservoir["A1"])
        m300.dispense(150, plate[f"A{n}"].top())
    m300.drop_tip()
