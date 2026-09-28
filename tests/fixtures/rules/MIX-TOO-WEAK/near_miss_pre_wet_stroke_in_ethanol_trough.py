# WHAT THIS TESTS (should NOT fire)
# A bead wash. The tip is pre-wetted with one stroke of 200 ul in the ethanol reservoir before
# the ethanol is shared out over the bead wells from above. One stroke in a trough that holds
# one liquid and is only ever drawn from is a pre-wet, not a mix: there is nothing there to mix.
from opentrons import protocol_api

metadata = {"protocolName": "Bead wash: ethanol from a pre-wetted tip", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    ethanol = protocol.define_liquid("ethanol", "80% ethanol", "#1f77b4")
    reservoir["A1"].load_liquid(ethanol, 10000)
    wells = [plate[f"A{n}"] for n in range(1, 9)]
    for n, well in enumerate(wells, start=1):
        beads = protocol.define_liquid(f"beads with library {n}", "AMPure beads bound to DNA", "#8c564b")
        well.load_liquid(beads, 50)

    p300.pick_up_tip()
    p300.mix(1, 200, reservoir["A1"])
    for well in wells:
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, well.top())
    p300.drop_tip()
