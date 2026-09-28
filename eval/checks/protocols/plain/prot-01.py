from opentrons import protocol_api

metadata = {
    "protocolName": "SDS-PAGE sample prep (12 samples)",
    "author": "Lab",
    "description": "15 ul protein sample + 5 ul 4x loading dye in a PCR plate.",
    "apiLevel": "2.19",
}

N = 12
SAMPLE_VOL = 15
DYE_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "PCR plate (SDS-PAGE samples)")
    sample_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Protein sample plate")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "Loading dye tube rack")
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    dye = protocol.define_liquid("4x loading dye", "4x Laemmli SDS loading dye with reducing agent", "#2C3E9E")
    tubes["A1"].load_liquid(dye, 100)  # 12 x 5 ul = 60 ul plus excess

    sources = sample_plate.rows()[0][:N]  # A1-A12
    dests = pcr_plate.rows()[0][:N]       # A1-A12
    for i, well in enumerate(sources):
        liq = protocol.define_liquid(
            f"Protein sample {i + 1}", f"Protein sample {i + 1} ({well.well_name})",
            "#%02X%02X%02X" % (240 - i * 12, 100 + i * 10, 70),
        )
        well.load_liquid(liq, 50)

    # 1. Loading dye (viscous: pipette slowly) into the empty wells with one tip
    p20.pick_up_tip()
    for d in dests:
        p20.aspirate(DYE_VOL, tubes["A1"], rate=0.5)
        protocol.delay(seconds=1)
        p20.dispense(DYE_VOL, d, rate=0.5)
        p20.blow_out(d.bottom(3))
    p20.drop_tip()

    # 2. Samples, fresh tip each, mix with the dye
    for s, d in zip(sources, dests):
        p20.pick_up_tip()
        p20.aspirate(SAMPLE_VOL, s)
        p20.dispense(SAMPLE_VOL, d)
        p20.mix(5, 15, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    protocol.comment("Seal the plate, heat 5 min at 95 C, spin down and load the gel.")
