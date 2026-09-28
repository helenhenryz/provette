# WHAT THIS TESTS (should FIRE, as a note; no warning)
# Four restriction digests in a PCR plate (the right plate). The request says the reagents are
# in tubes at 4 C; the protocol declares the enzyme in a channel of a 12-channel reservoir, next
# to the water and the buffer (which belong in a trough and are not flagged).
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    trough = protocol.load_labware("nest_12_reservoir_15ml", 2, "reagents")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5, "plasmids")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "digests")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    water = protocol.define_liquid("water", "nuclease-free water", "#ccc")
    buffer = protocol.define_liquid("10x buffer", "CutSmart", "#0cc")
    enzyme = protocol.define_liquid("restriction enzyme", "EcoRI", "#f80")
    trough["A1"].load_liquid(water, 5000)
    trough["A2"].load_liquid(buffer, 1000)
    trough["A3"].load_liquid(enzyme, 500)
    tubes = ["A1", "B1", "C1", "D1"]
    for i, tube in enumerate(tubes, 1):
        plasmid = protocol.define_liquid(f"plasmid {i}", "miniprep", "#08f")
        rack[tube].load_liquid(plasmid, 30)

    wells = ["A1", "B1", "C1", "D1"]
    p20.pick_up_tip()
    for well in wells:
        p20.aspirate(12, trough["A1"])
        p20.dispense(12, plate[well].top())
    p20.drop_tip()
    p20.pick_up_tip()
    for well in wells:
        p20.aspirate(2, trough["A2"])
        p20.dispense(2, plate[well].top())
    p20.drop_tip()
    for tube, well in zip(tubes, wells):
        p20.pick_up_tip()
        p20.aspirate(5, rack[tube])
        p20.dispense(5, plate[well])
        p20.drop_tip()
    for well in wells:
        p20.pick_up_tip()
        p20.aspirate(1, trough["A3"])
        p20.dispense(1, plate[well])
        p20.mix(5, 10, plate[well])
        p20.drop_tip()
