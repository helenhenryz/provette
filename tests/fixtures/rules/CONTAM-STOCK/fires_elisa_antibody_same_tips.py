# WHAT THIS TESTS (should FIRE, as an error)
# An ELISA plate: three columns of samples are moved from a sample plate to the assay plate, a
# fresh set of tips per column. Then the detection antibody is added to all three columns with
# ONE set of tips, dispensing at the bottom of wells that already hold sample, and going back to
# the antibody reservoir each time. After the first column the tips carry sample, so the
# reservoir is contaminated, and columns 2 and 3 get antibody that holds traces of column 1.
# Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "ELISA: detection antibody with one set of tips", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "sample plate")
    assay = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 5)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2", "A3"]
    for column in columns:
        m300.transfer(100, samples[column], assay[column], new_tip="always")

    antibody = reservoir["A1"]
    m300.pick_up_tip()
    for column in columns:
        m300.aspirate(100, antibody)
        m300.dispense(100, assay[column])  # default height: 1 mm, under the sample
    m300.drop_tip()
