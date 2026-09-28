"""Steps whose volume, or whose place, is not what the line seems to say.

All of these are accepted by the simulator at the API levels most published protocols use.
"""

metadata = {"protocolName": "Odd volumes and unnamed places", "apiLevel": "2.13"}


def run(protocol):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    p300.pick_up_tip()
    # "Empty the tip back into the source" with an empty tip: the tip goes into the well and
    # moves 0 uL. For contamination it still counts: the tip touched the liquid.
    p300.dispense(p300.current_volume, reservoir["A1"])

    # Asking for more than the tip holds: up to API 2.16 the robot dispenses what it has (90).
    p300.aspirate(90, reservoir["A1"])
    p300.dispense(200, plate["A1"])

    # No place named: the robot acts where the tip already is.
    p300.move_to(plate["A2"].bottom(2))
    p300.aspirate(30)  # from A2, 2 mm up
    p300.dispense(30)  # back into A2
    p300.mix(2, 20)  # still A2
    p300.blow_out()  # still A2
    p300.dispense(60, plate["A3"])  # the tip is empty: it goes into A3 and dispenses nothing
    p300.drop_tip()
