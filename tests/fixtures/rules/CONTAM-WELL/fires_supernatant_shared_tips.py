# WHAT THIS TESTS (should FIRE, as a warning)
# A bead wash on a magnet. Three columns of different samples were moved into the plate with
# fresh tips. Then the supernatant is removed from all three columns with ONE set of tips, to
# save tips. The tips go down into column 1, empty into the waste, and go down into column 2
# still wet with column 1. Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Bead wash: supernatant off with one set of tips", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("nest_96_wellplate_2ml_deep", 1, "sample plate")
    mag_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 2, "plate on the magnet")
    waste = protocol.load_labware("nest_1_reservoir_195ml", 3, "liquid waste")
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 5)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2", "A3"]
    for column in columns:
        m300.transfer(200, samples[column], mag_plate[column], new_tip="always")

    m300.pick_up_tip()
    for column in columns:
        m300.aspirate(180, mag_plate[column])
        m300.dispense(180, waste["A1"].top())
    m300.drop_tip()
