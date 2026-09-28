# WHAT THIS TESTS (should FIRE, as a warning)
# Colony PCR for 8 colonies: 20 ul of PCR mix and 1 ul of colony into a plate the author calls
# the "PCR plate" but loads as nest_96_wellplate_200ul_flat. Every well holds what the plate map
# asks for; the plate cannot go in a thermocycler.
from opentrons import protocol_api

requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "tubes")
    colonies = protocol.load_labware("nest_96_wellplate_200ul_flat", 5, "colony plate")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, "PCR plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("PCR master mix", "2x mix with primers", "#00f")
    rack["A1"].load_liquid(mix, 300)
    wells = [f"{row}1" for row in "ABCDEFGH"]
    for i, well in enumerate(wells, 1):
        colony = protocol.define_liquid(f"colony {i}", "resuspended colony", "#0a0")
        colonies[well].load_liquid(colony, 50)

    p20.pick_up_tip()
    for well in wells:
        p20.aspirate(20, rack["A1"])
        p20.dispense(20, plate[well].top())
    p20.drop_tip()
    for well in wells:
        p20.pick_up_tip()
        p20.aspirate(1, colonies[well])
        p20.dispense(1, plate[well])
        p20.mix(3, 10, plate[well])
        p20.drop_tip()
