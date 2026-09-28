"""An 8-channel pipette that does not always carry eight tips.

Two ways that happens. The protocol can tell the pipette to use only one of its nozzles. Or the
single-channel pipette has already taken tips from the column the 8-channel then picks up: the
simulator does not mind, and the 8-channel comes up with fewer tips. Provette must list only the
tips that are really there, and only the wells they really enter.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Partial tip pickup"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300m = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    # The single-channel pipette uses the first two tips of rack column 1.
    p300.transfer(30, reservoir["A1"], plate["A12"])  # takes tip A1, throws it away
    p300.transfer(30, reservoir["A1"], plate["B12"], trash=False)  # takes B1, puts it BACK, used

    # Only the front nozzle of the 8-channel: it behaves like a single-channel pipette.
    p300m.configure_nozzle_layout(style=protocol_api.SINGLE, start="H1", tip_racks=[tips])
    p300m.pick_up_tip()  # takes C1
    p300m.aspirate(30, reservoir["A2"])
    p300m.dispense(30, plate["C1"])
    p300m.drop_tip()

    # All eight nozzles again, sent to column 1 of the rack: A1 and C1 are gone, B1 is a used
    # tip that was put back. It comes up with six tips, one of them dirty.
    p300m.configure_nozzle_layout(style=protocol_api.ALL, tip_racks=[tips])
    p300m.pick_up_tip(tips["A1"])
    p300m.aspirate(30, reservoir["A3"])
    p300m.dispense(30, plate["A5"])  # only rows B, D, E, F, G, H get liquid
    p300m.return_tip()
