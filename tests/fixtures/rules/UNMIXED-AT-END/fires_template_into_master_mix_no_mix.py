# WHAT THIS TESTS (should FIRE, as a note)
# A PCR set-up: 18 ul of master mix into eight wells, then 2 ul of template DNA into each, and
# the run ends. The template sits under the master mix. The template is a sample, which would
# make this a warning, but the well holds "PCR master mix", and a PCR plate is usually vortexed
# and spun before cycling: a note.
from opentrons import protocol_api

metadata = {"protocolName": "PCR set-up, template never mixed in", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    master_mix = protocol.define_liquid("PCR master mix", "2x, with primers", "#2ca02c")
    tubes["A1"].load_liquid(master_mix, 300)
    templates = tubes.wells()[6:14]
    for i, tube in enumerate(templates):
        template = protocol.define_liquid(f"template DNA {i + 1}", "extracted DNA", "#d62728")
        tube.load_liquid(template, 50)

    wells = plate.columns()[0]
    p20.transfer(18, tubes["A1"], wells, new_tip="once")
    for tube, well in zip(templates, wells):
        p20.transfer(2, tube, well, new_tip="always")
