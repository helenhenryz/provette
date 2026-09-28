# WHAT THIS TESTS (should NOT fire)
# A two-fold dilution down a column written with bare aspirate and dispense calls, the way many
# older protocols are. There is no `mix` call anywhere: the author mixes by hand, drawing liquid
# up and pushing it back into the same well three times. That is mixing, and the rule has to
# see it. Old API (2.11), 8-channel pipette, no liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Two-fold dilution, mixed by hand", "apiLevel": "2.11"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    columns = [plate[f"A{n}"] for n in range(1, 5)]
    m300.transfer(100, reservoir["A1"], columns[1:], new_tip="once")  # diluent
    m300.transfer(200, reservoir["A2"], columns[0], new_tip="once")  # the top standard

    m300.pick_up_tip()
    for source, dest in zip(columns[:-1], columns[1:]):
        m300.aspirate(100, source)
        m300.dispense(100, dest)
        for _ in range(3):
            m300.aspirate(80, dest)
            m300.dispense(80, dest)
        m300.blow_out(dest.top())
    m300.drop_tip()
