# WHAT THIS TESTS (should NOT fire)
# A working stock is made on the deck (900 ul of PBS and 100 ul of drug in a tube) and mixed
# properly. Then, for each well, a fresh P300 tip takes one stroke of 100 ul in that tube and at
# once draws 100 ul from it. The stroke is a prime: it wets the tip with what it is about to
# carry, and claims nothing about the tube. One stroke a fifth of the pipette would fire on its
# own; followed by a draw from the same well with the same tip, it is not a mix at all.
from opentrons import protocol_api

metadata = {"protocolName": "Dose wells from a working stock, priming the tip", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    tips1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips1000])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    pbs = protocol.define_liquid("PBS", "diluent", "#1f77b4")
    drug = protocol.define_liquid("drug", "stock at 10 mM", "#d62728")
    reservoir["A1"].load_liquid(pbs, 10000)
    tubes["A1"].load_liquid(drug, 500)
    working = tubes["A2"]

    p1000.transfer(900, reservoir["A1"], working, new_tip="always")
    p1000.transfer(100, tubes["A1"], working, new_tip="always")
    p1000.pick_up_tip()
    p1000.mix(5, 800, working)
    p1000.drop_tip()

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    p300.transfer(100, reservoir["A1"], wells, new_tip="once")
    for well in wells:
        p300.pick_up_tip()
        p300.mix(1, 100, working)
        p300.aspirate(100, working)
        p300.dispense(100, well)
        p300.mix(5, 160, well)
        p300.drop_tip()
