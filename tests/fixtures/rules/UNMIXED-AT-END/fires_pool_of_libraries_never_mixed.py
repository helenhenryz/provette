# WHAT THIS TESTS (should FIRE, as a warning)
# A pool: 12 libraries, 5 to 20 ul each by concentration, into one empty tube, one after the
# other with a fresh tip each, and the run ends. The tube is only ever poured into and never
# drawn from, which is what a pool is, so it is not a sink. The last library in is 5 ul of a
# 145 ul pool (3%), nothing mixes the tube, and a library is a sample: nothing later will mix
# it, and a pool that is not mixed is not an equimolar pool. A warning.
from opentrons import protocol_api

metadata = {"protocolName": "Library pool, never mixed", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])

    volumes = [20, 15, 10, 5, 20, 15, 10, 5, 20, 15, 10, 5]  # by measured concentration
    sources = plate.columns()[0] + plate.columns()[1][:4]
    for i, well in enumerate(sources):
        library = protocol.define_liquid(f"library {i + 1}", "indexed library", "#2ca02c")
        well.load_liquid(library, 40)

    pool = tubes["A1"]
    for well, ul in zip(sources, volumes):
        p20.transfer(ul, well, pool, new_tip="always")
