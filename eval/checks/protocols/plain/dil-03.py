from opentrons import protocol_api

metadata = {
    "protocolName": "BSA standard curve - 1:2 serial dilution",
    "author": "Lab",
    "description": "8 BSA standards from 2 mg/ml in 1:2 steps in water, 50 ul final per well (A1-A8).",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

NUM_POINTS = 8
FINAL_VOL = 50


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1, "Tube rack: BSA stock + water")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "Assay plate")
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)

    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    bsa_stock = tubes["A1"]
    water = tubes["A2"]

    # Liquids
    bsa_liq = protocol.define_liquid(
        name="BSA stock 2 mg/ml", description="Bovine serum albumin, 2 mg/ml", display_color="#D62728"
    )
    water_liq = protocol.define_liquid(
        name="Water", description="Diluent (ultrapure water)", display_color="#AEC7E8"
    )
    bsa_stock.load_liquid(bsa_liq, volume=500)
    water.load_liquid(water_liq, volume=1000)

    # Standards in A1-A8: 2, 1, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625 mg/ml
    wells = plate.rows()[0][:NUM_POINTS]

    # 1. 50 ul water into wells 2-8
    p300.pick_up_tip()
    for well in wells[1:]:
        p300.aspirate(FINAL_VOL, water.bottom(2))
        p300.dispense(FINAL_VOL, well.bottom(1))
        p300.blow_out(well.top(-2))
    p300.drop_tip()

    # 2. 100 ul of 2 mg/ml stock into well 1 (half is carried forward)
    p300.pick_up_tip()
    p300.aspirate(2 * FINAL_VOL, bsa_stock.bottom(2), rate=0.5)
    p300.dispense(2 * FINAL_VOL, wells[0].bottom(1), rate=0.5)
    p300.blow_out(wells[0].top(-2))
    p300.drop_tip()

    # 3. Serial 1:2 transfers, fresh tip per step; gentle mixing (protein foams)
    for src, dest in zip(wells[:-1], wells[1:]):
        p300.pick_up_tip()
        p300.aspirate(FINAL_VOL, src.bottom(1), rate=0.5)
        p300.dispense(FINAL_VOL, dest.bottom(1), rate=0.5)
        p300.mix(5, 60, dest.bottom(1), rate=0.5)
        p300.blow_out(dest.top(-2))
        p300.drop_tip()

    # 4. Remove the extra 50 ul from the last well so every well holds 50 ul
    p300.pick_up_tip()
    p300.aspirate(FINAL_VOL, wells[-1].bottom(1), rate=0.5)
    p300.drop_tip()  # discard liquid with the tip

    protocol.comment("Standards ready in A1-A8 (2 -> 0.0156 mg/ml), 50 ul each.")
