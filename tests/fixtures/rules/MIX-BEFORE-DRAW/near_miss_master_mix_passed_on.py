# WHAT THIS TESTS (should NOT fire)
# Liquid added to an EMPTY well has nothing to mix with. A ready-made master mix is put into an
# empty tube on a cold block, and later shared out from that tube into a plate. It was
# dispensed and then drawn with no mixing in between: and that is fine, because it is one
# liquid. New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Master mix moved to a cold tube, then shared out"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    cold = protocol.load_module("temperature module gen2", 4)
    cold_rack = cold.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    master_mix = protocol.define_liquid("master mix", "ready to use", "#00AA00")
    rack["A1"].load_liquid(master_mix, 800)

    cold.set_temperature(4)
    p300.transfer(200, rack["A1"], cold_rack["A1"])
    p300.transfer(200, rack["A1"], cold_rack["A1"])  # a second helping of the same liquid
    p300.transfer(40, cold_rack["A1"], [plate[f"A{n}"] for n in range(1, 9)], new_tip="once")
