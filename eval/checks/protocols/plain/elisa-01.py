from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA sample and standard addition",
    "author": "Lab",
    "description": "100 ul of 40 serum samples into matching wells of a coated ELISA plate, plus 8 standards from tubes into column 12.",
    "apiLevel": "2.19",
}

VOL = 100
N_SAMPLES = 40  # A1-H5 (columns 1-5)


def run(protocol: protocol_api.ProtocolContext):
    elisa = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "Coated ELISA plate")
    source = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Serum sample plate")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "Standards tube rack")
    tips_multi = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips_single = protocol.load_labware("opentrons_96_tiprack_300ul", 5)

    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips_multi])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_single])

    # Liquids
    sample_wells = source.wells()[:N_SAMPLES]
    for i, well in enumerate(sample_wells):
        liq = protocol.define_liquid(
            f"Serum sample {i + 1}", f"Serum sample {i + 1} ({well.well_name})",
            "#%02X%02X%02X" % (250 - i * 3, 90 + i * 4, 60 + (i % 8) * 15),
        )
        well.load_liquid(liq, 150)

    std_tubes = tubes.wells()[:8]  # A1-D1, A2-D2 = standard 1 (highest) ... 8
    for i, tube in enumerate(std_tubes):
        liq = protocol.define_liquid(
            f"Standard {i + 1}", f"ELISA standard {i + 1} of 8 (standard curve point)",
            "#%02X%02X%02X" % (40, 60 + i * 20, 230 - i * 20),
        )
        tube.load_liquid(liq, 500)

    # 1. Standards into column 12 (A12 = standard 1 ... H12 = standard 8)
    for tube, dest in zip(std_tubes, elisa.columns_by_name()["12"]):
        p300.pick_up_tip()
        p300.mix(2, 100, tube)
        p300.aspirate(VOL, tube)
        p300.dispense(VOL, dest)
        p300.blow_out(dest.top(-2))
        p300.drop_tip()

    # 2. 40 samples = 5 full columns, 8-channel, matching wells, fresh tips per column
    for c in range(N_SAMPLES // 8):
        src = source.rows()[0][c]
        dst = elisa.rows()[0][c]
        m300.pick_up_tip()
        m300.mix(2, 80, src)
        m300.aspirate(VOL, src)
        m300.dispense(VOL, dst)
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    protocol.comment("Samples and standards added. Cover the plate and incubate as your ELISA kit specifies.")
