# WHAT THIS TESTS (should FIRE, as a warning)
# A 1:2 serial dilution written for 200 ul wells, run in a NEST 100 ul PCR plate: every well
# gets 100 ul of diluent and then 100 ul from the well before, so it holds 200 ul, twice the
# maker's stated maximum but under the 217 ul the well holds to its rim. The plate map
# verifies (the volumes add up); the simulator says nothing. This is the shape of a Super
# draft in eval/agent that was "verified 12 of 12".
from opentrons import protocol_api

metadata = {"protocolName": "dilution in a 100 ul plate", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "diluent", "#1f77b4")
    drug = protocol.define_liquid("drug", "stock", "#d62728")
    reservoir["A1"].load_liquid(pbs, 5000)
    tubes["A1"].load_liquid(drug, 500)

    wells = [plate[f"A{n}"] for n in range(1, 13)]
    p300.pick_up_tip()
    for well in wells:
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, well)
    p300.drop_tip()
    p300.pick_up_tip()
    p300.aspirate(100, tubes["A1"])
    p300.dispense(100, wells[0])
    for source, dest in zip(wells[:-1], wells[1:]):
        p300.mix(3, 80, source)
        p300.aspirate(100, source)
        p300.dispense(100, dest)
    p300.drop_tip()
