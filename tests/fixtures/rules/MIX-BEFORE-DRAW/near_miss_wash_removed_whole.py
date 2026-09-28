# WHAT THIS TESTS (should NOT fire)
# An ELISA wash. Wash buffer is added on top of what is left in the wells, and then ALL of it is
# taken out again and thrown away, with no mixing: on purpose. The rule is about drawing liquid
# of the wrong concentration and using it. Liquid that is removed completely, or goes to the
# waste, has no concentration anyone cares about. Fresh tips per column, so nothing else is
# wrong here either. Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "ELISA wash: add buffer, remove it all", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "sample plate")
    assay = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    waste = protocol.load_labware("nest_1_reservoir_195ml", 6, "liquid waste")
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 5)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2"]
    for column in columns:
        m300.transfer(50, samples[column], assay[column], new_tip="always")
    for column in columns:
        m300.pick_up_tip()
        m300.aspirate(200, reservoir["A1"])
        m300.dispense(200, assay[column].top())  # wash buffer on top of the sample
        m300.aspirate(250, assay[column])  # and all of it out again
        m300.dispense(250, waste["A1"].top())
        m300.drop_tip()
