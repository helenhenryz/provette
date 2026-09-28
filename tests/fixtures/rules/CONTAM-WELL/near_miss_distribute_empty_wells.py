# WHAT THIS TESTS (should NOT fire)
# Plate filling. One tip shares a buffer out into a whole row of EMPTY wells with `distribute`,
# from above, going back to the buffer between batches: the tip only ever meets that one
# buffer. Four different samples are then added, a fresh tip each. Last, a stop solution is
# added to the four wells with ONE tip, from the top of the well (`well.top()`): the tip never
# touches the samples. Old API (2.11), single-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Plate filling: distribute, samples, reagent from above", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    row = [plate[f"A{n}"] for n in range(1, 13)]
    p300.distribute(80, reservoir["A1"], [well.top() for well in row], new_tip="once")
    p300.transfer(20, [rack[t] for t in ["A1", "A2", "A3", "A4"]], row[:4], new_tip="always")

    p300.pick_up_tip()
    for well in row[:4]:
        p300.aspirate(50, reservoir["A2"])
        p300.dispense(50, well.top())
        p300.blow_out(well.top())
    p300.drop_tip()
