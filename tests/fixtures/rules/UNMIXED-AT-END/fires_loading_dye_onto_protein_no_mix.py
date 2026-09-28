# WHAT THIS TESTS (should FIRE, as a note)
# Gel samples: 15 ul of protein sample into eight wells, then 5 ul of 4x loading dye on top of
# each (25% of the well), and the run ends. Dye on protein in a 20 ul well does not mix on its
# own, and nothing will mix it before it is loaded on the gel. The catalogue makes this a
# warning by the technique (Protein), but the plate map does not carry a technique yet, and the
# liquid added last is the dye, a reagent, not a sample: so the rule as built says a note.
from opentrons import protocol_api

metadata = {"protocolName": "Loading dye onto protein, never mixed", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    dye = protocol.define_liquid("4x loading dye", "Laemmli sample buffer", "#9467bd")
    tubes["A1"].load_liquid(dye, 200)
    samples = tubes.wells()[6:14]
    for i, tube in enumerate(samples):
        protein = protocol.define_liquid(f"protein sample {i + 1}", "cell lysate", "#ff7f0e")
        tube.load_liquid(protein, 60)

    wells = plate.columns()[0]
    for tube, well in zip(samples, wells):
        p20.transfer(15, tube, well, new_tip="always")
    for well in wells:
        p20.transfer(5, tubes["A1"], well, new_tip="always")
