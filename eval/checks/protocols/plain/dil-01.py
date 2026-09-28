from opentrons import protocol_api

metadata = {
    "protocolName": "1:2 serial dilution, 12 points across row A",
    "author": "Lab",
    "description": "Two-fold serial dilution of a drug stock in PBS across row A, 100 ul final per well.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

FINAL_VOL = 100


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 2, "Dilution plate")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3, "PBS reservoir")
    rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 5, "Drug stock")

    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    pbs = reservoir["A1"]
    drug = rack["A1"]

    pbs_liq = protocol.define_liquid("PBS", "Phosphate-buffered saline diluent", "#1F77B4")
    drug_liq = protocol.define_liquid("Drug stock", "Drug stock at the top concentration of the series", "#D62728")
    pbs.load_liquid(pbs_liq, 5000)
    drug.load_liquid(drug_liq, 500)

    row = plate.rows()[0]  # A1..A12

    # 1. 100 ul PBS into wells 2-12
    p300.transfer(FINAL_VOL, pbs, row[1:], new_tip="once")

    # 2. 200 ul drug stock into well 1 (point 1 = undiluted stock)
    p300.pick_up_tip()
    p300.aspirate(2 * FINAL_VOL, drug)
    p300.dispense(2 * FINAL_VOL, row[0])
    p300.blow_out(row[0].top(-2))
    p300.drop_tip()

    # 3. Carry 100 ul across the row, mixing after each step; fresh tip per step
    for src, dst in zip(row[:-1], row[1:]):
        p300.pick_up_tip()
        p300.aspirate(FINAL_VOL, src)
        p300.dispense(FINAL_VOL, dst)
        p300.mix(5, 100, dst)
        p300.blow_out(dst.top(-2))
        if dst is row[-1]:
            # 4. remove the extra 100 ul from the last well so every well holds 100 ul
            p300.aspirate(FINAL_VOL, dst)
        p300.drop_tip()

    protocol.comment("Done. Row A holds a 12-point 1:2 series, 100 ul per well.")
