# WHAT THIS TESTS (should NOT fire)
# A two-fold serial dilution down a row with ONE tip, mixing after each step. The tip is wet
# with well 1 when it goes into well 2: but it is also *carrying* well 1's liquid into well 2
# on purpose. Everything the tip brings arrives in the liquid it dispenses, so nothing is
# there that was not meant to be. (Whether a tip should be reused down a dilution is a question
# the sources disagree on, docs/rule-sources.md; it is not this rule's question.)
# Old API (2.11), single-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Serial dilution, one tip", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    row = [plate[f"A{n}"] for n in range(1, 9)]
    p300.transfer(100, reservoir["A1"], row[1:], new_tip="once")  # diluent into wells 2 to 8
    p300.transfer(200, reservoir["A2"], row[0])  # the stock solution into well 1
    p300.transfer(100, row[:-1], row[1:], mix_after=(3, 80), new_tip="once")
