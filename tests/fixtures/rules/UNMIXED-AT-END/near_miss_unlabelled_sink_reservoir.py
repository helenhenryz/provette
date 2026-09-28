# WHAT THIS TESTS (should NOT fire)
# A dilution series where the excess from every step (50 ul of sample in buffer, then 50 ul of
# ethanol at the end) goes into channel A12 of the reservoir, which the author never names as
# waste. The channel holds several liquids in layers and the run ends, but it is a reservoir
# channel the robot only ever pours into and never draws from: a sink, whatever it is called, so
# there is nothing to say about it. The plate wells are mixed after every addition, so they are
# silent too.
from opentrons import protocol_api

metadata = {"protocolName": "Dilution with an unlabelled waste channel", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    buffer = protocol.define_liquid("assay buffer", "1x", "#1f77b4")
    ethanol = protocol.define_liquid("ethanol", "70%", "#7f7f7f")
    serum = protocol.define_liquid("serum sample", "patient 1", "#ff7f0e")
    reservoir["A1"].load_liquid(buffer, 5000)
    reservoir["A2"].load_liquid(ethanol, 5000)
    tubes["A1"].load_liquid(serum, 300)

    wells = plate.columns()[0][:4]
    p300.transfer(100, reservoir["A1"], wells, new_tip="once")
    p300.transfer(100, tubes["A1"], wells[0], new_tip="always", mix_after=(5, 150))
    for source, dest in zip(wells[:-1], wells[1:]):
        p300.transfer(100, source, dest, new_tip="always", mix_after=(5, 150))
    p300.transfer(50, wells, reservoir["A12"], new_tip="always")  # the excess, unnamed channel
    p300.transfer(50, reservoir["A2"], reservoir["A12"], new_tip="once")  # ethanol on top
