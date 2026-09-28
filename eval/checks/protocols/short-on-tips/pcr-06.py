from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep (16 colonies)",
    "author": "Lab",
    "description": "20 ul PCR mix into 16 wells, then 1 ul of each colony resuspension.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

N = 16


def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    colonies = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Colony resuspensions")
    pcr = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3, "PCR plate")
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips])

    mix = protocol.define_liquid("PCR mix", "Colony PCR mix with primers and polymerase", "#1f77b4")
    tubes["A1"].load_liquid(mix, 400)
    src = colonies.wells()[:N]   # A1-H1, A2-H2
    dst = pcr.wells()[:N]        # same positions in the PCR plate
    for i, well in enumerate(src):
        liq = protocol.define_liquid(f"Colony {i + 1}", f"Colony resuspension {i + 1} ({well.well_name})",
                                     "#%02x%02x40" % (250 - i * 10, 60 + i * 10))
        well.load_liquid(liq, 50)

    # 16 tips total. The PCR mix is dispensed into EMPTY wells with one tip;
    # that tip has only seen PCR mix, so it is reused for colony 1.
    # Each colony then gets its own tip (no way around that).
    p20.pick_up_tip()
    for d in dst:
        p20.aspirate(20, tubes["A1"])
        p20.dispense(20, d)
        p20.blow_out(d.top(-2))

    for s, d in zip(src, dst):
        if not p20.has_tip:
            p20.pick_up_tip()
        p20.mix(2, 10, s)          # resuspend the colony
        p20.aspirate(1, s)
        p20.dispense(1, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()
