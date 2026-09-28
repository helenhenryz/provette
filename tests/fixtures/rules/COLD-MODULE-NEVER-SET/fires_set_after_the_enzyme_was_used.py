# WHAT THIS TESTS (should FIRE)
# Twelve restriction digests are assembled from an enzyme, a buffer and plasmids held on a
# temperature module; set_temperature(4) is called only after the last digest is built. Every
# draw from the block happened on a warm module. One warning, saying at which line the module
# was finally set and that the liquids had already been used by then.
from opentrons import protocol_api

metadata = {"protocolName": "digests, module set too late", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    temp_module = protocol.load_module("temperature module gen2", 3)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "enzymes")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    water_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    enzyme = protocol.define_liquid("EcoRI enzyme", "20 U/ul in 50% glycerol", "#9467bd")
    buffer = protocol.define_liquid("CutSmart buffer", "10x", "#8c564b")
    plasmid = protocol.define_liquid("plasmid DNA", "miniprep, 50 ng/ul", "#d62728")
    water = protocol.define_liquid("water", "nuclease free", "#1f77b4")
    block["A1"].load_liquid(enzyme, 50)
    block["A2"].load_liquid(buffer, 200)
    plasmids = [well for column in block.columns()[2:5] for well in column]  # 12 tubes
    for tube in plasmids:
        tube.load_liquid(plasmid, 30)
    water_rack["A1"].load_liquid(water, 1500)

    digests = [plate[f"B{n}"] for n in range(1, 13)]
    p20.pick_up_tip()
    for well in digests:
        p20.aspirate(15, water_rack["A1"])
        p20.dispense(15, well)
    p20.drop_tip()
    p20.pick_up_tip()
    for well in digests:
        p20.aspirate(2, block["A2"])
        p20.dispense(2, well)
    p20.drop_tip()
    for tube, well in zip(plasmids, digests):
        p20.pick_up_tip()
        p20.aspirate(2, tube)
        p20.dispense(2, well)
        p20.drop_tip()
    for well in digests:
        p20.pick_up_tip()
        p20.aspirate(1, block["A1"])
        p20.dispense(1, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
    temp_module.set_temperature(4)
    protocol.delay(minutes=60)
