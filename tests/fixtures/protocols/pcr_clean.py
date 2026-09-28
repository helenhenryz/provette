"""PCR setup done properly: master mix first with one clean tip, then a fresh tip per sample."""

from opentrons import protocol_api

metadata = {"protocolName": "PCR setup (clean)"}
requirements = {"robotType": "OT-2", "apiLevel": "2.27"}

SAMPLE_TUBES = ["B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2"]


def run(protocol: protocol_api.ProtocolContext):
    temp_mod = protocol.load_module("temperature module gen2", 4)
    plate = temp_mod.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    mm = protocol.define_liquid("PCR master mix", description="2x master mix", display_color="#00FF00")
    rack["A1"].load_liquid(mm, 1000)
    samples = [rack[t] for t in SAMPLE_TUBES]
    for i, tube in enumerate(samples):
        s = protocol.define_liquid(f"sample {i + 1}", description=f"patient sample {i + 1}", display_color="#FF00%02X" % (i * 30))
        tube.load_liquid(s, 100)

    wells = [plate[f"A{i + 1}"] for i in range(8)]
    temp_mod.set_temperature(4)  # keep the enzyme cold
    p300.transfer(40, rack["A1"], wells, new_tip="once")  # master mix into empty wells: one tip is fine
    p300.transfer(20, samples, wells, new_tip="always", mix_after=(5, 50))  # a fresh tip per sample, mixed properly
    protocol.delay(minutes=5)
    temp_mod.deactivate()
