# WHAT THIS TESTS (should NOT fire)
# The same ELISA as fires_elisa_antibody_same_tips.py, done properly: the detection antibody is
# added with a fresh set of tips for every column. No tip that has touched a sample ever goes
# back into the antibody reservoir. Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "ELISA: detection antibody, fresh tips per column", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "sample plate")
    assay = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 5)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2", "A3"]
    for column in columns:
        m300.transfer(100, samples[column], assay[column], new_tip="always")
    for column in columns:
        m300.transfer(100, reservoir["A1"], assay[column], new_tip="always")
