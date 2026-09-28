# WHAT THIS TESTS (should FIRE)
# A 1:2 serial dilution in 200 ul: every well holds 100 ul of PBS, 100 ul comes in from the well
# before, and the well is mixed with `mix(5, 30)`. Five strokes is enough; 30 ul of 200 is not.
# Every step is the same line of the loop, so this is one finding with eight occurrences. The
# plate is a 360 ul flat plate so that the wells have room.
from opentrons import protocol_api

metadata = {"protocolName": "Two-fold dilution series, weakly mixed", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "diluent", "#1f77b4")
    drug = protocol.define_liquid("drug", "stock at 1 mM", "#d62728")
    reservoir["A1"].load_liquid(pbs, 5000)
    tubes["A1"].load_liquid(drug, 500)

    wells = [plate[f"A{n}"] for n in range(1, 9)]
    p300.transfer(100, reservoir["A1"], wells, new_tip="once")
    sources = [tubes["A1"]] + wells[:-1]
    for source, dest in zip(sources, wells):
        p300.pick_up_tip()
        p300.aspirate(100, source)
        p300.dispense(100, dest)
        p300.mix(5, 30, dest)
        p300.drop_tip()
