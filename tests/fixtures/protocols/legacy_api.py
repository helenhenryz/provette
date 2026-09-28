"""The same kind of job written for API level 2.11.

Most of the public Opentrons protocol library was written between 2019 and 2023 at API levels
like this one. Below level 2.14 the simulator runs a different, older engine, so Provette tests
that it reads both the same way.
"""

metadata = {"protocolName": "Old API level", "apiLevel": "2.11"}


def run(protocol):
    cold_block = protocol.load_module("temperature module gen2", 4)
    cold_plate = cold_block.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, label="assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tips_multi = protocol.load_labware("opentrons_96_tiprack_300ul", 6)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300m = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips_multi])

    cold_block.set_temperature(4)

    # One tip, used by hand.
    p300.pick_up_tip()
    p300.aspirate(50, cold_plate["A1"])
    p300.air_gap(10)
    p300.dispense(60, plate["A1"].top())  # from above the well: the tip stays clean
    p300.blow_out()
    p300.touch_tip()
    p300.return_tip()

    # A transfer with a mix.
    p300.transfer(30, reservoir["A2"], plate["A2"], mix_after=(2, 20))

    # Eight channels at once.
    p300m.pick_up_tip()
    p300m.aspirate(100, reservoir["A1"])
    p300m.dispense(100, plate["A3"])
    p300m.drop_tip()

    protocol.delay(minutes=2)
    cold_block.deactivate()
