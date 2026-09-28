from opentrons import protocol_api

metadata = {
    "protocolName": "96-well PCR setup: master mix + template",
    "author": "Lab",
    "description": "18 ul master mix from a reservoir plus 2 ul template from the matching well of a 96-well sample plate into every well of a PCR plate.",
    "apiLevel": "2.19",
}

MM_VOL = 18
TEMPLATE_VOL = 2


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "PCR plate")
    sample_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Template sample plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3, "Master mix reservoir")
    tips = [protocol.load_labware("opentrons_96_filtertiprack_20ul", s) for s in (4, 5)]

    m20 = protocol.load_instrument("p20_multi_gen2", "left", tip_racks=tips)

    # Liquids
    mm = protocol.define_liquid("PCR master mix", "PCR master mix (polymerase, dNTPs, primers, buffer)", "#1F77B4")
    reservoir["A1"].load_liquid(mm, 2500)  # 96 x 18 ul = 1728 ul plus dead volume

    for i, well in enumerate(sample_plate.wells()):
        hue = "#%02X%02X%02X" % (60 + (i * 2) % 190, 200 - (i % 12) * 12, 80 + (i % 8) * 20)
        liq = protocol.define_liquid(
            f"Template {well.well_name}", f"DNA template sample in well {well.well_name}", hue
        )
        well.load_liquid(liq, 20)

    # 1. Master mix into all 96 wells (empty wells, so one set of tips)
    m20.pick_up_tip()
    for col in pcr_plate.rows()[0]:
        m20.aspirate(MM_VOL, reservoir["A1"])
        m20.dispense(MM_VOL, col)
        m20.blow_out(col.top(-2))
    m20.drop_tip()

    # 2. Template from the matching well, fresh tips per column, mix
    for src, dst in zip(sample_plate.rows()[0], pcr_plate.rows()[0]):
        m20.pick_up_tip()
        m20.aspirate(TEMPLATE_VOL, src)
        m20.dispense(TEMPLATE_VOL, dst)
        m20.mix(3, 10, dst)
        m20.blow_out(dst.top(-2))
        m20.drop_tip()

    protocol.comment("Seal the PCR plate, spin down briefly and transfer to the thermocycler.")
