# WHAT THIS TESTS (should NOT fire)
# One tip tops up four wells of master mix with water, touching the mix each time. The tip
# carries water (a carrier) and, after the first well, mix back into the water tube. Nothing
# it carries is a sample, so this rule stays silent; CONTAM-STOCK still sees the water tube.
from opentrons import protocol_api

metadata = {"protocolName": "water into mix wells with one tip", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    mix = protocol.define_liquid("PCR master mix", "2x master mix with polymerase", "#2ca02c")
    water = protocol.define_liquid("nuclease-free water", "molecular biology grade", "#1f77b4")
    tubes["A1"].load_liquid(mix, 500)
    tubes["A2"].load_liquid(water, 1000)

    wells = [plate[f"A{n}"] for n in range(1, 5)]
    p20.transfer(15, tubes["A1"], wells, new_tip="once")
    p20.transfer(5, tubes["A2"], wells, new_tip="once")  # one tip, into the mix each time
