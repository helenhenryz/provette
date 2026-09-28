from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 48 sequencing libraries (5 ul each) into one tube",
    "author": "Lab",
    "description": "5 ul of each of 48 indexed libraries (plate columns 1-6) pooled into one 1.5 ml tube.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N_LIBRARIES = 48
POOL_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    tips20 = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    lib_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Library plate")
    rack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", 3, "Pool tube")

    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])

    pool = rack["A1"]  # empty 1.5 ml tube
    libraries = lib_plate.wells()[:N_LIBRARIES]  # A1-H1 ... A6-H6

    for i, well in enumerate(libraries):
        liq = protocol.define_liquid(
            f"Library {i + 1}", f"Indexed sequencing library {i + 1} ({well.well_name})", "#17BECF")
        well.load_liquid(liq, 20)

    # Fresh filter tip for every library to avoid index cross-contamination
    for well in libraries:
        p20.pick_up_tip()
        p20.aspirate(POOL_VOL, well)
        p20.dispense(POOL_VOL, pool)
        p20.blow_out(pool.bottom(8))
        p20.touch_tip(pool, v_offset=-3)
        p20.drop_tip()

    # Mix the 240 ul pool
    p300.pick_up_tip()
    p300.mix(10, 150, pool)
    p300.blow_out(pool.top(-5))
    p300.drop_tip()

    protocol.comment("Done. 240 ul pool in tube A1 of the rack in slot 3.")
