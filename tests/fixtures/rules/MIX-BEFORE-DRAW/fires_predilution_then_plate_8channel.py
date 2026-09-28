# WHAT THIS TESTS (should FIRE, as a warning)
# Samples are pre-diluted 1 in 5 in a dilution plate (buffer first, then sample on top), and
# 50 uL of each pre-dilution is then moved on to the assay plate. Nothing mixes the dilution
# plate in between: the sample is sitting where the tip left it. What goes to the assay plate
# is not a 1 in 5 dilution. Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Pre-dilution without mixing, 8-channel", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    samples = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "sample plate")
    dilution = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "dilution plate")
    assay = protocol.load_labware("corning_96_wellplate_360ul_flat", 5, "assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = [protocol.load_labware("opentrons_96_tiprack_300ul", slot) for slot in (4, 7)]
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=tips)

    columns = ["A1", "A2"]
    m300.transfer(160, reservoir["A1"], [dilution[c] for c in columns], new_tip="once")
    for column in columns:
        m300.transfer(40, samples[column], dilution[column], new_tip="always")
    for column in columns:
        m300.transfer(50, dilution[column], assay[column], new_tip="always")
