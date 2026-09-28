"""An 8-channel pipette fills a plate from a reservoir.

An 8-channel pipette has eight tips in a row, front to back. When the protocol says
"aspirate from plate A1", all eight tips go down: into A1, B1, C1 ... H1. In a reservoir,
where one trough is as long as a whole plate column, all eight tips go into the same trough.
The simulator only names the first well; Provette has to work out the other seven.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Multi-channel: reservoir to plate"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, label="assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    plate384 = protocol.load_labware("corning_384_wellplate_112ul_flat", 4)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300m = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    buffer = protocol.define_liquid("buffer", description="PBS", display_color="#0000FF")
    reservoir["A1"].load_liquid(buffer, 10000)

    # Column 1 of the plate: eight wells filled in one move.
    p300m.pick_up_tip()  # takes the eight tips of rack column 1
    p300m.aspirate(100, reservoir["A1"])  # eight tips, one trough
    p300m.dispense(100, plate["A1"])  # eight tips, wells A1 to H1
    p300m.drop_tip()

    # A 384-well plate has wells half as far apart, so the eight tips enter every other row.
    p300m.pick_up_tip()
    p300m.aspirate(40, reservoir["A1"])
    p300m.dispense(20, plate384["A1"])  # rows A, C, E, G, I, K, M, O
    p300m.dispense(20, plate384["B1"])  # rows B, D, F, H, J, L, N, P
    p300m.return_tip()
