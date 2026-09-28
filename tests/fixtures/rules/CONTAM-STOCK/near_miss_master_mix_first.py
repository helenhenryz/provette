# WHAT THIS TESTS (should NOT fire)
# The right order for a qPCR set-up. The master mix goes into the EMPTY wells first, all with
# one tip: that tip goes back into the master mix tube many times, but the only liquid it has
# ever touched is master mix. Then each sample is added with a fresh tip and mixed.
# New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "qPCR set-up: master mix first"}
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
    p300.transfer(40, rack["D1"], wells, new_tip="once")
    p300.transfer(20, [rack[t] for t in SAMPLE_TUBES], wells, new_tip="always", mix_after=(3, 30))
