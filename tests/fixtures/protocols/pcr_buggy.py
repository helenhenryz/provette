"""PCR setup with a biology bug: ONE tip goes through all eight patient samples and the master mix.

The simulator is happy with this. Every sample after the first is contaminated, and so is the
master mix tube.
"""

from opentrons import protocol_api

metadata = {"protocolName": "PCR setup (buggy: one tip)"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}

SAMPLE_TUBES = ["B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2"]


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    mm = protocol.define_liquid("PCR master mix", description="2x master mix", display_color="#00FF00")
    rack["A1"].load_liquid(mm, 1000)
    for i, t in enumerate(SAMPLE_TUBES):
        s = protocol.define_liquid(f"sample {i+1}", description=f"patient sample {i+1}", display_color="#FF00%02X" % (i * 30))
        rack[t].load_liquid(s, 100)

    p300.pick_up_tip()
    for i, t in enumerate(SAMPLE_TUBES):
        dest = plate[f"A{i+1}"]
        p300.aspirate(20, rack[t])
        p300.dispense(20, dest)
        p300.aspirate(40, rack["A1"])
        p300.dispense(40, dest)
    p300.drop_tip()
