from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep (16 colonies)",
    "author": "Lab",
    "description": "20 ul PCR mix into 16 wells, then 1 ul of each of 16 colony resuspensions.",
    "apiLevel": "2.19",
}

N = 16
MIX_VOL = 20
COLONY_VOL = 1


def run(protocol: protocol_api.ProtocolContext):
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1, "PCR plate")
    colony_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Colony resuspension plate")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, "PCR mix tube rack")
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 4)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Liquids
    pcr_mix = protocol.define_liquid("PCR mix", "Complete colony PCR mix (polymerase, primers, dNTPs, buffer)", "#1F77B4")
    tubes["A1"].load_liquid(pcr_mix, 400)  # 16 x 20 ul = 320 ul plus excess

    sources = colony_plate.wells()[:N]   # A1-H1, A2-H2
    dests = pcr_plate.wells()[:N]        # same positions in the PCR plate

    for i, well in enumerate(sources):
        liq = protocol.define_liquid(
            f"Colony {i + 1}", f"Colony {i + 1} resuspended in water ({well.well_name})",
            "#%02X%02X%02X" % (230 - i * 10, 120 + i * 6, 40 + i * 8),
        )
        well.load_liquid(liq, 50)

    # 1. PCR mix into 16 empty wells, one tip
    p20.pick_up_tip()
    for d in dests:
        p20.aspirate(MIX_VOL, tubes["A1"])
        p20.dispense(MIX_VOL, d)
        p20.blow_out(d.top(-2))
    p20.drop_tip()

    # 2. 1 ul of each colony resuspension, fresh tip each, mix
    for s, d in zip(sources, dests):
        p20.pick_up_tip()
        p20.mix(2, 10, s)  # resuspend cells that have settled
        p20.aspirate(COLONY_VOL, s)
        p20.dispense(COLONY_VOL, d)
        p20.mix(3, 10, d)
        p20.blow_out(d.top(-2))
        p20.drop_tip()

    protocol.comment("Seal the plate and run the colony PCR programme.")
