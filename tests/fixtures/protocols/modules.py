"""Modules: the parts of the robot that heat, cool and shake.

Nothing here moves much liquid. What matters to Provette is *when* each temperature was set,
and how long the run waited, because enzymes left warm for too long stop working.
"""

from opentrons import protocol_api

metadata = {"protocolName": "Temperature module, thermocycler, heater-shaker"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}


def run(protocol: protocol_api.ProtocolContext):
    cold_block = protocol.load_module("temperature module gen2", 6)
    cold_plate = cold_block.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", label="reagents on ice")
    cycler = protocol.load_module("thermocyclerModuleV2")  # always sits in slots 7, 8, 10, 11
    pcr_plate = cycler.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")
    shaker = protocol.load_module("heaterShakerModuleV1", 1)
    shaker_plate = shaker.load_labware("opentrons_96_flat_bottom_adapter_nest_wellplate_200ul_flat")
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 9)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    cold_block.set_temperature(4)
    cycler.open_lid()
    shaker.close_labware_latch()  # the robot refuses to pipette next to an open latch

    p300.pick_up_tip()
    p300.aspirate(50, cold_plate["A1"])
    p300.dispense(25, pcr_plate["A1"])
    p300.dispense(25, shaker_plate["A1"])
    p300.drop_tip()

    shaker.set_and_wait_for_temperature(37)
    shaker.set_and_wait_for_shake_speed(500)
    protocol.delay(seconds=30)
    shaker.deactivate_shaker()
    shaker.deactivate_heater()
    shaker.open_labware_latch()

    cycler.close_lid()
    cycler.set_lid_temperature(105)
    cycler.set_block_temperature(95, hold_time_seconds=120)
    cycler.execute_profile(
        steps=[
            {"temperature": 95, "hold_time_seconds": 15},
            {"temperature": 60, "hold_time_seconds": 30},
        ],
        repetitions=3,
        block_max_volume=25,
    )
    cycler.set_block_temperature(4)
    cycler.open_lid()
    protocol.pause("Take the plate out")
    protocol.delay(minutes=1)
    cycler.deactivate()
    cold_block.deactivate()
