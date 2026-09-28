# WHAT THIS TESTS (should NOT fire)
# 120 ul of PBS and 100 ul of serum in a 360 ul flat well, mixed with `mix(10, 100)`. Each
# stroke is 45% of the well, under the half the rule once asked for; but ten of them move 4.5
# wells' worth of liquid in all, and that does mix the well. This is the shape of every false
# alarm in the flood over 787 public protocols: a stroke of 36 to 48% repeated 4 to 10 times.
from opentrons import protocol_api

metadata = {"protocolName": "Serum diluted in PBS, mixed with ten small strokes", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "diluent", "#1f77b4")
    reservoir["A1"].load_liquid(pbs, 5000)
    sera = [tubes[f"A{n}"] for n in range(1, 7)]
    for n, tube in enumerate(sera, start=1):
        serum = protocol.define_liquid(f"serum {n}", "patient serum", "#d62728")
        tube.load_liquid(serum, 300)

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    p300.transfer(120, reservoir["A1"], wells, new_tip="once")
    for tube, well in zip(sera, wells):
        p300.pick_up_tip()
        p300.aspirate(100, tube)
        p300.dispense(100, well)
        p300.mix(10, 100, well)
        p300.drop_tip()
