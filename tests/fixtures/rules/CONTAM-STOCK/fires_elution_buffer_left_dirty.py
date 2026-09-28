# WHAT THIS TESTS (should FIRE, but only as a warning)
# The end of a bead clean-up. The tip resuspends the beads of one sample, and then the SAME tip
# goes into the shared elution buffer tube to fetch buffer for that sample. The buffer tube now
# holds a little of the sample. The protocol never draws from the buffer again, so nothing in
# this run is harmed: but the tube is left dirty for whoever uses it next.
# New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Bead clean-up: elution with a used tip"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    library = protocol.define_liquid("library on beads", "DNA library bound to beads", "#884400")
    buffer = protocol.define_liquid("elution buffer", "10 mM Tris", "#0000FF")
    plate["A1"].load_liquid(library, 50)
    rack["A1"].load_liquid(buffer, 1000)

    p300.pick_up_tip()
    p300.mix(5, 30, plate["A1"])  # resuspend the beads
    p300.aspirate(30, rack["A1"])  # the same, wet, tip goes into the buffer
    p300.dispense(30, plate["A1"])
    p300.drop_tip()
