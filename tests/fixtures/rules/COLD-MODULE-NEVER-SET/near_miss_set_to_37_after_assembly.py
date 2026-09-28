# WHAT THIS TESTS (should NOT fire)
# Twelve ligations are assembled at room temperature from a buffer, a ligase and inserts held in
# tubes on a temperature module, and only then is the module set to 37 C for an incubation.
# The module was set after its liquids were used, but to a warm setting: that is a planned
# incubation, not a forgotten cold block, so nothing to report.
from opentrons import protocol_api

metadata = {"protocolName": "ligations, then a 37 C incubation", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    temp_module = protocol.load_module("temperature module gen2", 3)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "reagents")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    water_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    ligase = protocol.define_liquid("T4 DNA ligase", "400 U/ul in 50% glycerol", "#9467bd")
    buffer = protocol.define_liquid("T4 ligase buffer", "10x, with ATP", "#8c564b")
    insert = protocol.define_liquid("insert DNA", "gel-purified fragment, 20 ng/ul", "#d62728")
    water = protocol.define_liquid("water", "nuclease free", "#1f77b4")
    block["A1"].load_liquid(ligase, 50)
    block["A2"].load_liquid(buffer, 200)
    inserts = [well for column in block.columns()[2:5] for well in column]  # 12 tubes
    for tube in inserts:
        tube.load_liquid(insert, 30)
    water_rack["A1"].load_liquid(water, 1500)

    reactions = [plate[f"C{n}"] for n in range(1, 13)]
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(15, water_rack["A1"])
        p20.dispense(15, well)
    p20.drop_tip()
    p20.pick_up_tip()
    for well in reactions:
        p20.aspirate(2, block["A2"])
        p20.dispense(2, well)
    p20.drop_tip()
    for tube, well in zip(inserts, reactions):
        p20.pick_up_tip()
        p20.aspirate(2, tube)
        p20.dispense(2, well)
        p20.drop_tip()
    for well in reactions:
        p20.pick_up_tip()
        p20.aspirate(1, block["A1"])
        p20.dispense(1, well)
        p20.mix(3, 10, well)
        p20.drop_tip()
    temp_module.set_temperature(37)
    protocol.delay(minutes=30)
    temp_module.deactivate()
