# WHAT THIS TESTS (should FIRE, as a note)
# A BSA standard curve for a protein assay: eight two-fold dilutions of the BSA standard in
# water, made across a row of a flat 360 ul plate, mixed at every step. No well on the plate
# holds water alone, so the curve has no blank: nothing to read the zero against. There is no
# master mix here, so this is the blank finding and not the no-template one.
from opentrons import protocol_api

metadata = {"protocolName": "BSA standard curve, no blank", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    bsa = protocol.define_liquid("BSA standard", "BSA 2 mg/ml", "#d62728")
    water = protocol.define_liquid("water", "deionised water", "#1f77b4")
    tubes["A1"].load_liquid(bsa, 500)
    tubes["A2"].load_liquid(water, 1500)

    curve = [plate[f"A{n}"] for n in range(1, 9)]

    p300.pick_up_tip()
    for well in curve:
        p300.aspirate(100, tubes["A2"])
        p300.dispense(100, well)
    p300.drop_tip()

    p300.pick_up_tip()
    p300.aspirate(100, tubes["A1"])
    p300.dispense(100, curve[0])
    for source, dest in zip(curve[:-1], curve[1:]):
        p300.mix(3, 80, source)
        p300.aspirate(100, source)
        p300.dispense(100, dest)
    p300.mix(3, 80, curve[-1])
    p300.drop_tip()
