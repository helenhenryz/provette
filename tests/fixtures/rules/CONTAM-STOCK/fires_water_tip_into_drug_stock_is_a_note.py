# WHAT THIS TESTS (should FIRE, as a note)
# A serial dilution: one tip hands out PBS to the empty wells, then goes into the drug stock to
# start the series. The tip carries PBS into the drug stock, which is carry-over, and the rule
# fires. But what was carried is the diluent that the stock is about to be diluted with, so
# the finding is a NOTE, not an error: severity follows what was carried (D-20).
from opentrons import protocol_api

metadata = {"protocolName": "PBS tip into the drug stock", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = protocol.define_liquid("PBS", "phosphate-buffered saline, the diluent", "#1f77b4")
    drug = protocol.define_liquid("drug", "drug stock at the top concentration", "#d62728")
    reservoir["A1"].load_liquid(pbs, 5000)
    tubes["A1"].load_liquid(drug, 500)

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    p300.pick_up_tip()
    for well in wells[1:]:
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, well)
    p300.aspirate(200, tubes["A1"])  # the PBS tip enters the drug stock: carry-over of PBS
    p300.dispense(200, wells[0])
    for source, dest in zip(wells[:-1], wells[1:]):
        p300.aspirate(100, source)
        p300.dispense(100, dest)
        p300.mix(3, 80, dest)
    p300.aspirate(100, wells[-1])
    p300.drop_tip()
