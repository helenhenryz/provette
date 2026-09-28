# WHAT THIS TESTS (should FIRE, as a warning)
# ELISA: 100 ul of each of 8 sera from tubes into a plate the author calls the "ELISA plate" but
# loads as nest_96_wellplate_100ul_pcr_full_skirt. The map verifies; a PCR plate is neither
# coated nor read.
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "sera")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "ELISA plate")
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    tubes = ["A1", "B1", "C1", "D1", "A2", "B2", "C2", "D2"]
    wells = [f"{row}1" for row in "ABCDEFGH"]
    for i, tube in enumerate(tubes, 1):
        serum = protocol.define_liquid(f"serum {i}", "patient serum", "#c00")
        rack[tube].load_liquid(serum, 300)

    for tube, well in zip(tubes, wells):
        p300.pick_up_tip()
        p300.aspirate(100, rack[tube])
        p300.dispense(100, plate[well])
        p300.drop_tip()
