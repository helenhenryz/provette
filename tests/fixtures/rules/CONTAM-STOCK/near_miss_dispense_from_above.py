# WHAT THIS TESTS (should NOT fire)
# One set of tips adds the detection antibody to three columns that already hold sample, and
# goes back to the reservoir each time: but it dispenses from the TOP of the well, above the
# liquid, and takes an air gap above the reservoir. The tip never touches a sample, so it
# carries nothing back. This is the pattern that made a naive check flag 117 of 150 public
# protocols (DECISIONS.md D-12). Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "ELISA: detection antibody from above", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "sample plate")
    assay = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 5)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2", "A3"]
    for column in columns:
        m300.transfer(100, samples[column], assay[column], new_tip="always")

    m300.pick_up_tip()
    for column in columns:
        m300.aspirate(100, reservoir["A1"])
        m300.air_gap(10)
        m300.dispense(110, assay[column].top())
        m300.blow_out(assay[column].top())
    m300.drop_tip()
