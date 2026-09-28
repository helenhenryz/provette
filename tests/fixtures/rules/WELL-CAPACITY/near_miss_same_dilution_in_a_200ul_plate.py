# WHAT THIS TESTS (should NOT fire)
# The same 1:2 dilution as fires_dilution_in_a_100ul_pcr_plate.py at half the volumes, in a
# 200 ul flat plate: every well holds 100 ul at its fullest, half of what the plate takes, so
# the mixing strokes have room.
from opentrons import protocol_api

metadata = {"protocolName": "dilution in a 200 ul plate", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "diluent", "#1f77b4")
    drug = protocol.define_liquid("drug", "stock", "#d62728")
    reservoir["A1"].load_liquid(pbs, 5000)
    tubes["A1"].load_liquid(drug, 500)

    wells = [plate[f"A{n}"] for n in range(1, 13)]
    p300.pick_up_tip()
    for well in wells:
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, well)
    p300.drop_tip()
    p300.pick_up_tip()
    p300.aspirate(50, tubes["A1"])
    p300.dispense(50, wells[0])
    for source, dest in zip(wells[:-1], wells[1:]):
        p300.mix(3, 40, source)
        p300.aspirate(50, source)
        p300.dispense(50, dest)
    p300.drop_tip()
