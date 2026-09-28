from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 48 sequencing libraries (5 ul each) into one tube",
    "description": "5 ul of each indexed library into a single 1.5 ml tube. 48 tips (one per library).",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 48


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "Library plate")
    rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2, "Pool tube")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    pool = rack["A1"]  # empty 1.5 ml tube
    libs = plate.wells()[:N]  # columns 1-6
    for i, w in enumerate(libs):
        liq = protocol.define_liquid(f"Library {i + 1}", f"Indexed sequencing library {i + 1}", "#9467bd")
        w.load_liquid(liq, 20)

    # A tip that has been in one library (or in the pool) must never enter
    # another library well, so one tip per library is the minimum that keeps
    # the source plate clean. No extra tip is spent on mixing: the last tip
    # mixes the pool.
    for i, w in enumerate(libs):
        p20.pick_up_tip()
        p20.aspirate(5, w)
        p20.dispense(5, pool.bottom(1))
        p20.mix(2, 5, pool.bottom(1))   # rinse the tip into the pool
        p20.blow_out(pool.bottom(8))
        if i == N - 1:
            p20.mix(15, 20, pool.bottom(2))
            p20.blow_out(pool.bottom(12))
        p20.drop_tip()

    protocol.comment("Pool = 240 ul. Vortex briefly and spin down before quantification.")
