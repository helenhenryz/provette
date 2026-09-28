from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay: 20 samples in duplicate + BSA standards",
    "author": "Lab",
    "description": "5 ul of each of 20 protein samples in duplicate, then 250 ul Bradford reagent to all 48 wells in use (8 pre-loaded BSA standard wells included).",
    "apiLevel": "2.19",
}

N_SAMPLES = 20
SAMPLE_VOL = 5
REAGENT_VOL = 250


def run(protocol: protocol_api.ProtocolContext):
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "Assay plate (flat)")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2, "Bradford reagent reservoir")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "Protein samples (1.5 ml tubes)")
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips300])

    # Liquids
    reagent = protocol.define_liquid("Bradford reagent", "Coomassie Bradford dye reagent", "#8B5A2B")
    # 48 wells x 250 ul = 12 ml, split over two reservoir wells (3 columns each)
    reservoir["A1"].load_liquid(reagent, 7500)
    reservoir["A2"].load_liquid(reagent, 7500)

    # BSA standards already in the plate, column 1 (A1-H1), 5 ul each
    std_conc = [0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    for i, (well, conc) in enumerate(zip(plate.columns()[0], std_conc)):
        liq = protocol.define_liquid(
            f"BSA standard {i + 1}", f"BSA standard {conc} mg/ml",
            "#%02X%02X%02X" % (30, 200 - i * 20, 90 + i * 20),
        )
        well.load_liquid(liq, SAMPLE_VOL)

    sample_tubes = tubes.wells()[:N_SAMPLES]
    for i, tube in enumerate(sample_tubes):
        liq = protocol.define_liquid(
            f"Protein sample {i + 1}", f"Protein sample {i + 1}",
            "#%02X%02X%02X" % (240 - i * 6, 80 + i * 7, 150),
        )
        tube.load_liquid(liq, 100)

    # Sample wells: columns 2-6 (40 wells); duplicates are vertically adjacent
    sample_wells = [w for col in plate.columns()[1:6] for w in col]

    # 1. Samples in duplicate
    for i, tube in enumerate(sample_tubes):
        p20.pick_up_tip()
        for dest in sample_wells[2 * i: 2 * i + 2]:
            p20.aspirate(SAMPLE_VOL, tube)
            p20.dispense(SAMPLE_VOL, dest)
            p20.blow_out(dest.bottom(3))
        p20.drop_tip()

    # 2. Bradford reagent to every used well (columns 1-6), fresh tips per column, mix
    for c in range(6):
        src = reservoir["A1"] if c < 3 else reservoir["A2"]
        dst = plate.rows()[0][c]
        m300.pick_up_tip()
        m300.aspirate(REAGENT_VOL, src)
        m300.dispense(REAGENT_VOL, dst)
        m300.mix(3, 150, dst, rate=0.7)
        m300.blow_out(dst.top(-2))
        m300.drop_tip()

    protocol.comment("Incubate 5-10 min at room temperature, then read absorbance at 595 nm.")
