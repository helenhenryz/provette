from opentrons import protocol_api

metadata = {
    "protocolName": "1:2 serial dilution, 12 points across row A",
    "description": "12-point two-fold dilution of a drug stock in PBS, 100 ul final per well. 1 tip in total.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1, "Dilution plate")
    res = protocol.load_labware("nest_12_reservoir_15ml", 2, "Reservoir")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "Drug stock")
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips])

    pbs_well = res["A1"]
    waste = res["A12"]
    drug_tube = rack["A1"]

    pbs = protocol.define_liquid("PBS", "Diluent", "#aec7e8")
    drug = protocol.define_liquid("Drug stock", "Drug at the top concentration of the series", "#d62728")
    pbs_well.load_liquid(pbs, 5000)     # 11 x 100 = 1.1 ml needed
    drug_tube.load_liquid(drug, 500)    # 200 ul needed

    row = plate.rows()[0]  # A1..A12

    # One tip for the whole run: PBS first (clean liquid into empty wells),
    # then the drug, then the dilution itself going from high to low
    # concentration, which is standard practice for two-fold series.
    p300.pick_up_tip()
    for w in row[1:]:
        p300.aspirate(100, pbs_well)
        p300.dispense(100, w)
    p300.blow_out(row[-1].top(-2))

    # Point 1 = undiluted stock
    p300.aspirate(200, drug_tube)
    p300.dispense(200, row[0])
    p300.blow_out(row[0].top(-2))

    for src, dst in zip(row[:-1], row[1:]):
        p300.aspirate(100, src)
        p300.dispense(100, dst)
        p300.mix(5, 80, dst)
        p300.blow_out(dst.top(-2))

    # Remove the extra 100 ul from the last well so every well holds 100 ul
    p300.aspirate(100, row[-1])
    p300.dispense(100, waste.top(-2))
    p300.blow_out(waste.top(-2))
    p300.drop_tip()
