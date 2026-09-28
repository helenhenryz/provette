from opentrons import protocol_api

metadata = {
    "protocolName": "SDS-PAGE sample prep (12 samples)",
    "author": "Lab",
    "description": "5 ul 4x loading dye + 15 ul protein sample per well of a PCR plate.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 12


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    samples = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Protein samples")
    pcr = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3, "PCR plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    dye = protocol.define_liquid("4x loading dye", "4x Laemmli loading dye", "#1f3fbf")
    tubes["A1"].load_liquid(dye, 200)
    src = samples.rows()[0][:N]     # A1-A12
    dst = pcr.rows()[0][:N]         # A1-A12
    for i, w in enumerate(src):
        liq = protocol.define_liquid(f"Protein sample {i + 1}", f"Protein sample {i + 1} ({w.well_name})",
                                     "#%02x%02x50" % (240 - i * 15, 70 + i * 14))
        w.load_liquid(liq, 50)

    # 13 tips: one for the dye (dispensed into the empty wells first),
    # then one per sample, which also does the mixing.
    p20.pick_up_tip()
    for d in dst:
        p20.aspirate(5, tubes["A1"], rate=0.5)
        p20.dispense(5, d, rate=0.5)
    p20.blow_out(dst[-1].top(-2))
    p20.drop_tip()

    for s, d in zip(src, dst):
        p20.pick_up_tip()
        p20.aspirate(15, s)
        p20.dispense(15, d)
        p20.mix(3, 15, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()
