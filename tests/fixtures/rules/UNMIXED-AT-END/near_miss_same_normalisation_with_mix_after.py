# WHAT THIS TESTS (should NOT fire)
# The same normalisation as fires_normalisation_dna_under_water_never_mixed.py, but the DNA
# transfer mixes each well after the addition: `mix_after=(5, 20)` (a P20 cannot draw the 30 ul
# the catalogue wrote). The mixing strokes are the same tip going up and down in the same well;
# the rule has to see them and stay silent.
from opentrons import protocol_api

metadata = {"protocolName": "DNA normalisation, mixed after", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    water = protocol.define_liquid("nuclease-free water", "diluent", "#1f77b4")
    reservoir["A1"].load_liquid(water, 5000)
    dna_ul = [2 + (i * 18) // 23 for i in range(24)]  # 2 to 20 ul, by concentration
    for i, tube in enumerate(tubes.wells()[:24]):
        dna = protocol.define_liquid(f"DNA {i + 1}", "genomic DNA to normalise", "#d62728")
        tube.load_liquid(dna, 100)

    wells = plate.wells()[:24]
    p300.pick_up_tip()
    for well, ul in zip(wells, dna_ul):
        p300.aspirate(50 - ul, reservoir["A1"])
        p300.dispense(50 - ul, well)
    p300.drop_tip()
    for tube, well, ul in zip(tubes.wells()[:24], wells, dna_ul):
        p20.transfer(ul, tube, well, new_tip="always", mix_after=(5, 20))
