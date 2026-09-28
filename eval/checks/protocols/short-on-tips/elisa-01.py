from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA sample and standard addition",
    "author": "Lab",
    "description": "100 ul of 40 sera into matching wells (columns 1-5) and 8 standards into column 12.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    # One tip rack shared by both pipettes
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    source = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, "Serum source plate")
    elisa = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "Coated ELISA plate")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "Standards")
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # 40 sera = columns 1-5 (A1-H5) of the source plate
    for i, well in enumerate(source.wells()[:40]):
        liq = protocol.define_liquid(f"Serum {i + 1}", f"Serum sample {i + 1} ({well.well_name})",
                                     "#%02x%02x30" % (255 - i * 4, 80 + i * 4))
        well.load_liquid(liq, 150)
    # Standards in tubes A1..D2 (column order), LOWEST concentration (blank) first
    std_tubes = tubes.wells()[:8]
    for i, t in enumerate(std_tubes):
        liq = protocol.define_liquid(f"Standard {i + 1}", f"Standard {i + 1} (1 = blank/lowest, 8 = highest)",
                                     "#%02x%02xff" % (220 - i * 25, 220 - i * 25))
        t.load_liquid(liq, 500)

    # Samples: 8-channel, one set of tips per column (each serum needs its own tip) = 40 tips
    for col in range(5):
        m300.pick_up_tip()
        m300.aspirate(100, source.rows()[0][col])
        m300.dispense(100, elisa.rows()[0][col])
        m300.blow_out(elisa.rows()[0][col].top(-2))
        m300.drop_tip()

    # Standards: ONE tip, going strictly from the lowest to the highest
    # concentration into empty wells (standard 1 -> A12 ... standard 8 -> H12).
    # The trace carried up the series
    # is negligible against a more concentrated standard.
    p300.starting_tip = tips["A6"]
    p300.pick_up_tip()
    for t, d in zip(std_tubes, elisa.columns()[11]):
        p300.aspirate(100, t)
        p300.dispense(100, d)
        p300.blow_out(d.top(-2))
    p300.drop_tip()
