from opentrons import protocol_api

metadata = {
    "protocolName": "BSA standard curve (1:2 serial dilution, 8 points)",
    "description": "2 mg/ml down to 0.0156 mg/ml, 50 ul per well",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_POINTS = 8
FINAL_VOL = 50


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    tubes = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 2)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 1)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    bsa_t, water_t = tubes["A1"], tubes["B1"]
    bsa_t.load_liquid(protocol.define_liquid(
        "BSA stock 2 mg/ml", "BSA standard stock, 2 mg/ml", "#d62728"), 500)
    water_t.load_liquid(protocol.define_liquid(
        "Water", "Diluent (water)", "#aec7e8"), 1000)

    wells = plate.rows()[0][:N_POINTS]  # A1 (2 mg/ml) ... A8 (0.0156 mg/ml)

    # A single tip does everything:
    #  - water first (tip is clean, wells are empty)
    #  - then BSA stock, then the dilution series from high to low. The tip has
    #    just been equilibrated by mixing in the well it next aspirates from,
    #    so carry-over does not bias the series.
    p300.pick_up_tip()
    for w in wells[1:]:
        p300.aspirate(FINAL_VOL, water_t.bottom(2))
        p300.dispense(FINAL_VOL, w.bottom(1))
        p300.blow_out(w.top(-2))
    p300.blow_out(protocol.fixed_trash)

    p300.aspirate(2 * FINAL_VOL, bsa_t.bottom(2))
    p300.dispense(2 * FINAL_VOL, wells[0].bottom(1))
    p300.blow_out(wells[0].top(-2))

    for src, dst in zip(wells[:-1], wells[1:]):
        p300.aspirate(FINAL_VOL, src.bottom(1))
        p300.dispense(FINAL_VOL, dst.bottom(1))
        p300.mix(5, 60, dst.bottom(1))
        p300.blow_out(dst.top(-2))

    # last well holds 100 ul: discard 50 ul so every well ends at 50 ul
    p300.aspirate(FINAL_VOL, wells[-1].bottom(1))
    p300.drop_tip()
