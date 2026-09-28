# WHAT THIS TESTS (should FIRE, as a note)
# The protocol declares 500 ul of sample in a well of a 200 ul flat plate. The robot moves
# only 20 ul of it, so nothing overflows, but the prep sheet cannot be followed as written.
from opentrons import protocol_api

metadata = {"protocolName": "declared over the maximum", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    source = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    sample = protocol.define_liquid("sample 1", "serum", "#2ca02c")
    source["A1"].load_liquid(sample, 500)
    p20.transfer(20, source["A1"], plate["A1"], new_tip="always")
