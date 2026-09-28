# WHAT THIS TESTS (should FIRE, as an error)
# A qPCR set-up in the wrong order. The six DNA samples go into the plate first, each with a
# fresh tip: fine. Then the master mix is added to every well with ONE tip, and mixed in each
# well. The tip comes out of well 1 wet with sample 1 and goes straight back into the master mix
# tube, and so on: the master mix collects every sample, and every later well gets all the
# samples before it. New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "qPCR set-up: master mix last, one tip"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}

SAMPLE_TUBES = ["A1", "A2", "A3", "A4", "A5", "A6"]


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    master_mix = protocol.define_liquid("qPCR master mix", "2x mix with primers", "#00AA00")
    rack["D1"].load_liquid(master_mix, 500)
    for number, tube in enumerate(SAMPLE_TUBES, 1):
        dna = protocol.define_liquid(f"DNA sample {number}", "genomic DNA", "#AA0000")
        rack[tube].load_liquid(dna, 200)

    wells = [plate[f"B{n}"] for n in range(1, 7)]
    p300.transfer(20, [rack[t] for t in SAMPLE_TUBES], wells, new_tip="always")
    p300.transfer(40, rack["D1"], wells, new_tip="once", mix_after=(3, 30))
