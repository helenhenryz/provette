# WHAT THIS TESTS (should NOT fire)
# Bradford assay: 5 ul of each of 4 protein samples and 250 ul of Bradford reagent from a
# reservoir into corning_96_wellplate_360ul_flat. A flat plate is what a plate reader reads, and
# the reagent is a reagent in a trough for a technique that does not mind.
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 6)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "samples")
    trough = protocol.load_labware("nest_12_reservoir_15ml", 5, "reagent")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "assay plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    reagent = protocol.define_liquid("Bradford reagent", "Coomassie", "#a52")
    trough["A1"].load_liquid(reagent, 5000)
    tubes = ["A1", "B1", "C1", "D1"]
    for i, tube in enumerate(tubes, 1):
        sample = protocol.define_liquid(f"protein sample {i}", "lysate", "#0a0")
        rack[tube].load_liquid(sample, 50)

    wells = ["A1", "B1", "C1", "D1"]
    for tube, well in zip(tubes, wells):
        p20.pick_up_tip()
        p20.aspirate(5, rack[tube])
        p20.dispense(5, plate[well])
        p20.drop_tip()
    for well in wells:
        p300.pick_up_tip()
        p300.aspirate(250, trough["A1"])
        p300.dispense(250, plate[well])
        p300.mix(3, 100, plate[well])
        p300.drop_tip()
