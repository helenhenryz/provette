"""Tip racks that a person refills during the run.

The robot cannot see a tip rack. When a protocol says `reset_tipracks()`, or simply picks up
from a rack position it has already emptied (usually after a pause that says "replace the
tips"), it is trusting a person to have put a full rack there. The simulator accepts both.
Provette must keep following the tips, or every step after the refill would be invisible.
"""

metadata = {"protocolName": "Refilled tip racks", "apiLevel": "2.13"}


def run(protocol):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    p300.transfer(50, reservoir["A1"], plate["A1"])  # uses tip A1 and throws it away

    # The protocol says so: every rack is full again, start from A1.
    p300.reset_tipracks()
    p300.transfer(50, reservoir["A1"], plate["A2"])  # tip A1 again: a NEW tip in the same place

    # The protocol does not say so: it pauses, then picks up from A1 a third time.
    protocol.pause("Replace the tip rack in slot 3")
    p300.pick_up_tip(tips["A1"])
    p300.aspirate(50, reservoir["A1"])
    p300.dispense(50, plate["A3"])
    p300.drop_tip()
