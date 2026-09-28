# WHAT THIS TESTS (should FIRE, as a warning)
# Four patient samples sit in four wells. Before the next step each well has to be resuspended,
# and the author wrote the loop with ONE tip: mix well 1, mix well 2, mix well 3, mix well 4.
# The tip leaves a little of every sample in all the wells after it. No stock is involved, so
# only this rule can see it. New API (2.20), single-channel pipette, liquids declared.
from opentrons import protocol_api

metadata = {"protocolName": "Resuspend four samples with one tip"}
requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    wells = [plate[name] for name in ["A1", "A2", "A3", "A4"]]
    for number, well in enumerate(wells, 1):
        cells = protocol.define_liquid(f"patient cells {number}", "cell suspension", "#AA00AA")
        well.load_liquid(cells, 150)

    p300.pick_up_tip()
    for well in wells:
        p300.mix(3, 100, well)
    p300.drop_tip()
