from opentrons import protocol_api

metadata = {
    "protocolName": "Bradford assay, 20 samples in duplicate",
    "author": "Lab",
    "description": "5 ul sample in duplicate, then 250 ul Bradford reagent to the 40 sample wells and 8 BSA standard wells.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1, "Protein samples")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "Assay plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    sample_tubes = tubes.wells()[:20]
    for i, t in enumerate(sample_tubes):
        liq = protocol.define_liquid(f"Protein sample {i + 1}", f"Protein sample {i + 1}",
                                     "#%02x%02x50" % (250 - i * 9, 60 + i * 9))
        t.load_liquid(liq, 100)
    # BSA standards already in the plate: column 12, 5 ul each
    std_wells = plate.columns()[11]
    for i, w in enumerate(std_wells):
        liq = protocol.define_liquid(f"BSA standard {i + 1}", f"BSA standard {i + 1} (pre-loaded, 5 ul)",
                                     "#%02x%02xff" % (230 - i * 25, 230 - i * 25))
        w.load_liquid(liq, 5)
    bradford = protocol.define_liquid("Bradford reagent", "Coomassie Bradford reagent", "#8c564b")
    reservoir["A1"].load_liquid(bradford, 7500)
    reservoir["A2"].load_liquid(bradford, 7500)

    # Samples: duplicates are neighbouring wells down the columns 1-5
    # (sample 1 -> A1+B1, sample 2 -> C1+D1 ...). One tip per sample serves
    # both duplicates (wells are empty) = 20 tips.
    sample_wells = plate.wells()[:40]
    for i, t in enumerate(sample_tubes):
        p20.pick_up_tip()
        for d in sample_wells[2 * i: 2 * i + 2]:
            p20.aspirate(5, t)
            p20.dispense(5, d.bottom(0.5))
            p20.blow_out(d.bottom(2))
        p20.drop_tip()

    # Bradford reagent: ONE tip for all 48 wells. It is dispensed from the top
    # of the well and never touches the contents; the 250 ul jet mixes the 5 ul.
    targets = sample_wells + std_wells
    p300.pick_up_tip()
    for n, d in enumerate(targets):
        src = reservoir["A1"] if n < 24 else reservoir["A2"]
        p300.aspirate(250, src)
        p300.dispense(250, d.top(-1))
        p300.blow_out(d.top(-1))
    p300.drop_tip()
