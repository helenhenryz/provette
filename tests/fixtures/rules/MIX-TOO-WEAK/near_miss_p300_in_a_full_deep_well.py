# WHAT THIS TESTS (should NOT fire)
# 1,000 ul of medium and 500 ul of an overnight culture in a deep well, mixed with a P300 at
# `mix(5, 250)`. 250 ul is a sixth of the well, but the well holds more than the P300 can draw,
# so the stroke is judged against the pipette: 250 of 300 ul, five times, is as good as this
# pipette can do. Nothing to report.
from opentrons import protocol_api

metadata = {"protocolName": "Subculture: dilute an overnight culture 1:3", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    medium = protocol.define_liquid("LB", "LB medium", "#d4a017")
    reservoir["A1"].load_liquid(medium, 10000)
    cultures = [plate[f"H{n}"] for n in range(1, 7)]
    for n, well in enumerate(cultures, start=1):
        culture = protocol.define_liquid(f"culture {n}", "overnight E. coli culture", "#2ca02c")
        well.load_liquid(culture, 1500)

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    p1000.transfer(1000, reservoir["A1"], wells, new_tip="once")
    for culture, well in zip(cultures, wells):
        p1000.transfer(500, culture, well, new_tip="always")
        p300.pick_up_tip()
        p300.mix(5, 250, well)
        p300.drop_tip()
