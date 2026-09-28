# WHAT THIS TESTS (should FIRE)
# Gel samples: 15 ul of PCR product and 5 ul of 6x loading dye in a PCR plate, then
# `mix(3, 20)`. The stroke is the whole 20 ul: the tip draws air from the bottom of the well
# and foams the dye. Three strokes and 100% of the well, so only the whole-well test trips.
from opentrons import protocol_api

metadata = {"protocolName": "Gel samples: add loading dye", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    dye = protocol.define_liquid("loading dye", "6x DNA loading dye", "#1f77b4")
    tubes["A1"].load_liquid(dye, 200)
    products = [tubes[f"B{n}"] for n in range(1, 7)]
    for n, tube in enumerate(products, start=1):
        product = protocol.define_liquid(f"PCR product {n}", "amplified DNA", "#d62728")
        tube.load_liquid(product, 40)

    wells = [plate[f"A{n}"] for n in range(1, 7)]
    for tube, well in zip(products, wells):
        p20.transfer(15, tube, well, new_tip="always")
    for well in wells:
        p20.pick_up_tip()
        p20.aspirate(5, tubes["A1"])
        p20.dispense(5, well)
        p20.mix(3, 20, well)
        p20.drop_tip()
