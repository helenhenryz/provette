# WHAT THIS TESTS (should NOT fire)
# Four PCR reactions, 20 ul master mix and 5 ul of DNA each, into the NEST 100 ul PCR plate: the
# right plate for a PCR setup.
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "tubes")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "PCR plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("PCR master mix", "2x mix", "#00f")
    rack["A1"].load_liquid(mix, 200)
    tubes = ["A2", "B2", "C2", "D2"]
    for i, tube in enumerate(tubes, 1):
        dna = protocol.define_liquid(f"DNA sample {i}", "genomic DNA", "#0a0")
        rack[tube].load_liquid(dna, 30)

    wells = ["A1", "B1", "C1", "D1"]
    p20.pick_up_tip()
    for well in wells:
        p20.aspirate(20, rack["A1"])
        p20.dispense(20, plate[well].top())
    p20.drop_tip()
    for tube, well in zip(tubes, wells):
        p20.pick_up_tip()
        p20.aspirate(5, rack[tube])
        p20.dispense(5, plate[well])
        p20.mix(3, 10, plate[well])
        p20.drop_tip()
