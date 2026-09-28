# WHAT THIS TESTS (should FIRE, as a warning)
# Standards of 350 ul in a 360 ul flat well, mixed with 150 ul strokes. Nothing goes over the
# maximum on paper, but a well over nine tenths full spills when a tip mixes it.
from opentrons import protocol_api

metadata = {"protocolName": "mixing a full well", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    buffer = protocol.define_liquid("buffer", "assay buffer", "#1f77b4")
    standard = protocol.define_liquid("standard", "protein standard", "#ff7f0e")
    reservoir["A1"].load_liquid(buffer, 10000)
    reservoir["A2"].load_liquid(standard, 5000)

    for n in range(1, 5):
        well = plate[f"A{n}"]
        p300.transfer(300, reservoir["A1"], well, new_tip="once")
        p300.pick_up_tip()
        p300.aspirate(50, reservoir["A2"])
        p300.dispense(50, well)
        p300.mix(5, 150, well)  # 350 ul in a 360 ul well, stirred with 150 ul strokes
        p300.drop_tip()
