"""Four PCR reactions: 20 ul master mix + 5 ul of each DNA sample. Runs dry: 60 ul of master mix declared, 80 needed."""
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

SAMPLE_UL = 5
MIX_UL = 20


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 6)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "tubes")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "PCR plate")
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    mix = protocol.define_liquid("PCR master mix", "mix", "#00f")
    rack["A1"].load_liquid(mix, 60)
    sample_tubes = [rack[w] for w in ("A2", "B2", "C2", "D2")]
    for i, tube in enumerate(sample_tubes, start=1):
        tube.load_liquid(protocol.define_liquid(f"DNA sample {i}", "dna", "#0f0"), 30)

    dests = [plate[w] for w in ("A1", "B1", "C1", "D1")]
    p300.pick_up_tip()
    for dest in dests:
        p300.aspirate(MIX_UL, rack["A1"])
        p300.dispense(MIX_UL, dest)
    p300.drop_tip()
    for tube, dest in zip(sample_tubes, dests):
        p20.pick_up_tip()
        p20.aspirate(SAMPLE_UL, tube)
        p20.dispense(SAMPLE_UL, dest)
        p20.drop_tip()
