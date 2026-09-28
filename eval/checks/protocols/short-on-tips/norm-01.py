from opentrons import protocol_api

metadata = {
    "protocolName": "Normalize 24 DNA samples to 10 ng/ul in 50 ul",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

CONCS = [85, 120, 44, 67, 210, 95, 33, 150, 78, 60, 101, 55,
         190, 72, 48, 130, 88, 25, 64, 110, 39, 175, 92, 58]
TARGET = 10
FINAL_VOL = 50


def run(protocol: protocol_api.ProtocolContext):
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    src = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    dst = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    res = protocol.load_labware("nest_12_reservoir_15ml", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])

    water = res["A1"]
    water.load_liquid(protocol.define_liquid("Water", "Nuclease-free water", "#aec7e8"), 5000)
    for i, c in enumerate(CONCS):
        src.wells()[i].load_liquid(protocol.define_liquid(
            f"DNA sample {i + 1}", f"DNA sample {i + 1}, {c} ng/ul", "#2ca02c"), 40)

    sample_vols = [round(TARGET * FINAL_VOL / c, 2) for c in CONCS]   # 2.38 - 20 ul
    water_vols = [round(FINAL_VOL - v, 2) for v in sample_vols]       # 30 - 47.62 ul

    # 1) Water into the empty destination wells: ONE tip for all 24
    p300.pick_up_tip()
    for i, v in enumerate(water_vols):
        p300.aspirate(v, water.bottom(2))
        p300.dispense(v, dst.wells()[i].bottom(1))
        p300.blow_out(dst.wells()[i].top(-2))
    p300.drop_tip()

    # 2) Samples (same well position in the new plate): fresh tip per sample
    for i, v in enumerate(sample_vols):
        d = dst.wells()[i]
        p20.pick_up_tip()
        p20.aspirate(v, src.wells()[i].bottom(1))
        p20.dispense(v, d.bottom(1))
        p20.mix(5, 20, d.bottom(1))
        p20.blow_out(d.top(-2))
        p20.drop_tip()
