# WHAT THIS TESTS (should FIRE)
# Eight deep wells get 500 ul of LB medium, then 5 ul of a glycerol stock with a P20 and
# `mix_after=(3, 10)`. Three strokes of half the pipette would pass if the pipette were judged
# alone; but the P20's 20 ul is under a fifth of the 505 ul in the well, so no stroke it can make
# will mix the well however many times, and the fix names a P300. Before the pipette-cap clause
# was tightened this was silent.
from opentrons import protocol_api

metadata = {"protocolName": "Inoculate LB from a glycerol stock, three strokes", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    lb = protocol.define_liquid("LB", "LB medium", "#d4a017")
    stock = protocol.define_liquid("glycerol stock", "E. coli glycerol stock", "#2ca02c")
    reservoir["A1"].load_liquid(lb, 8000)
    tubes["A1"].load_liquid(stock, 500)

    wells = [plate[f"A{n}"] for n in range(1, 9)]
    p300.transfer(500, reservoir["A1"], wells, new_tip="once")
    p20.transfer(5, tubes["A1"], wells, new_tip="always", mix_after=(3, 10))
