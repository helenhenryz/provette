# WHAT THIS TESTS (should NOT fire)
# 50 ul of water and 50 ul of a DNA standard in a 200 ul flat well, mixed with `mix(3, 80)`:
# exactly three strokes of 80% of the well, the floor of the rule. Three is not fewer than
# three, 80 ul is not the whole well, and three strokes of 0.8 move 2.4 wells' worth, over the
# 2.0 the rule asks for (three of half the well would be 1.5, and would fire). Nothing to report.
from opentrons import protocol_api

metadata = {"protocolName": "Standard diluted 1:2 in water, mixed at the floor", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    water = protocol.define_liquid("water", "nuclease-free water", "#1f77b4")
    standard = protocol.define_liquid("DNA standard", "10^8 copies per ul", "#d62728")
    tubes["A1"].load_liquid(water, 1000)
    tubes["B1"].load_liquid(standard, 500)

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    p300.transfer(50, tubes["A1"], wells, new_tip="once")
    for well in wells:
        p300.pick_up_tip()
        p300.aspirate(50, tubes["B1"])
        p300.dispense(50, well)
        p300.mix(3, 80, well)
        p300.drop_tip()
