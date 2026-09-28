# WHAT THIS TESTS (should NOT fire)
# Eight PCRs are assembled straight into a plate on a thermocycler, from a tube rack on the
# deck, and then a profile is run. No temperature module is loaded, and the thermocycler's
# block is set by its profile, not by set_temperature: not this rule's business.
from opentrons import protocol_api

metadata = {"protocolName": "PCR on the thermocycler", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    cycler = protocol.load_module("thermocycler module")
    plate = cycler.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "reagents")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    master_mix = protocol.define_liquid("Q5 master mix", "2x hot-start polymerase mix", "#1f77b4")
    template = protocol.define_liquid("DNA template", "genomic DNA, 5 ng/ul", "#d62728")
    rack["A1"].load_liquid(master_mix, 400)
    rack["A2"].load_liquid(template, 50)

    cycler.open_lid()
    reactions = [plate[f"A{n}"] for n in range(1, 9)]
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(12.5, rack["A1"])
        p20.dispense(12.5, well)
    p20.drop_tip()
    for well in reactions:
        p20.pick_up_tip()
        p20.aspirate(5, rack["A2"])
        p20.dispense(5, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
    cycler.close_lid()
    cycler.set_lid_temperature(105)
    cycler.execute_profile(
        steps=[{"temperature": 98, "hold_time_seconds": 30}]
        + [
            {"temperature": 98, "hold_time_seconds": 10},
            {"temperature": 60, "hold_time_seconds": 20},
            {"temperature": 72, "hold_time_seconds": 30},
        ]
        * 30,
        repetitions=1,
        block_max_volume=20,
    )
    cycler.set_block_temperature(4)
    cycler.open_lid()
