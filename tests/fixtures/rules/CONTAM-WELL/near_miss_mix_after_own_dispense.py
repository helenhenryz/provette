# WHAT THIS TESTS (should NOT fire)
# Buffer is already in six wells. Each sample is added with its own fresh tip, and that tip
# then mixes the well it has just dispensed into. The tip is wet with sample while it is in the
# buffer: but the sample has just been put in that well on purpose.
# New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Add samples to buffer and mix, fresh tip each"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}

SAMPLE_TUBES = ["A1", "A2", "A3", "A4", "A5", "A6"]


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    buffer = protocol.define_liquid("assay buffer", "PBS", "#0000FF")
    reservoir["A1"].load_liquid(buffer, 10000)
    for number, tube in enumerate(SAMPLE_TUBES, 1):
        serum = protocol.define_liquid(f"serum {number}", "patient serum", "#AA0000")
        rack[tube].load_liquid(serum, 300)

    wells = [plate[f"C{n}"] for n in range(1, 7)]
    p300.transfer(90, reservoir["A1"], wells, new_tip="once")
    for tube, well in zip(SAMPLE_TUBES, wells):
        p300.pick_up_tip()
        p300.aspirate(30, rack[tube])
        p300.dispense(30, well)
        p300.mix(4, 80, well)
        p300.drop_tip()
