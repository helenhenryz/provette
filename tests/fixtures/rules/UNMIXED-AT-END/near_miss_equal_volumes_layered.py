# WHAT THIS TESTS (should NOT fire)
# 100 ul of buffer onto 100 ul of sample in eight wells of a 360 ul plate, no mix, and the run
# ends. The addition is half of the well: a volume that big stirs the well as it lands, the
# same reasoning as MIX-BEFORE-DRAW's whole-well threshold, so there is nothing to say.
from opentrons import protocol_api

metadata = {"protocolName": "Equal volumes, no mix", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    buffer = protocol.define_liquid("assay buffer", "1x", "#1f77b4")
    reservoir["A1"].load_liquid(buffer, 5000)
    samples = tubes.wells()[:8]
    for i, tube in enumerate(samples):
        sample = protocol.define_liquid(f"sample {i + 1}", "serum", "#ff7f0e")
        tube.load_liquid(sample, 300)

    wells = plate.columns()[0]
    for tube, well in zip(samples, wells):
        p300.transfer(100, tube, well, new_tip="always")
    p300.transfer(100, reservoir["A1"], wells, new_tip="always")
