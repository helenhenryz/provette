from opentrons import protocol_api

metadata = {
    "protocolName": "12 restriction digests (20 ul)",
    "author": "Lab",
    "description": "12 x 20 ul digests: 12 ul water, 2 ul 10x buffer, 5 ul plasmid (one per reaction), 1 ul enzyme. Reagents at 4 C on the temperature module.",
    "apiLevel": "2.19",
}

N = 12
WATER_VOL = 12
BUFFER_VOL = 2
PLASMID_VOL = 5
ENZYME_VOL = 1


def run(protocol: protocol_api.ProtocolContext):
    temp_mod = protocol.load_module("temperature module gen2", 3)
    cold = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap", "Reagents at 4 C")
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2, "Digest reactions (PCR plate)")
    tips = protocol.load_labware("opentrons_96_filtertiprack_20ul", 1)

    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Tube layout on the cold block
    water_tube = cold["A1"]
    buffer_tube = cold["B1"]
    enzyme_tube = cold["C1"]
    plasmid_tubes = [w for col in cold.columns()[1:4] for w in col]  # A2-D2, A3-D3, A4-D4

    water = protocol.define_liquid("Water", "Nuclease-free water", "#9ECAE1")
    water_tube.load_liquid(water, 500)      # 144 ul needed
    buf = protocol.define_liquid("10x buffer", "10x restriction enzyme buffer", "#FDB462")
    buffer_tube.load_liquid(buf, 50)        # 24 ul needed
    enz = protocol.define_liquid("Restriction enzyme", "Restriction enzyme in 50% glycerol", "#E41A1C")
    enzyme_tube.load_liquid(enz, 25)        # 12 ul needed
    for i, tube in enumerate(plasmid_tubes):
        liq = protocol.define_liquid(
            f"Plasmid {i + 1}", f"Plasmid DNA {i + 1} ({tube.well_name})",
            "#%02X%02X%02X" % (60 + i * 12, 170 - i * 8, 90 + i * 10),
        )
        tube.load_liquid(liq, 20)

    reactions = pcr_plate.rows()[0][:N]  # A1-A12; reaction n gets plasmid n

    temp_mod.set_temperature(4)

    # 1. Water (empty wells, one tip)
    p20.pick_up_tip()
    for r in reactions:
        p20.aspirate(WATER_VOL, water_tube)
        p20.dispense(WATER_VOL, r)
        p20.blow_out(r.bottom(3))
    p20.drop_tip()

    # 2. 10x buffer
    for r in reactions:
        p20.pick_up_tip()
        p20.aspirate(BUFFER_VOL, buffer_tube)
        p20.dispense(BUFFER_VOL, r)
        p20.mix(2, 8, r)
        p20.blow_out(r.top(-2))
        p20.drop_tip()

    # 3. Plasmids, a different one per reaction
    for tube, r in zip(plasmid_tubes, reactions):
        p20.pick_up_tip()
        p20.aspirate(PLASMID_VOL, tube)
        p20.dispense(PLASMID_VOL, r)
        p20.mix(2, 10, r)
        p20.blow_out(r.top(-2))
        p20.drop_tip()

    # 4. Enzyme last (viscous glycerol stock: slow), then mix the full reaction
    for r in reactions:
        p20.pick_up_tip()
        p20.aspirate(ENZYME_VOL, enzyme_tube, rate=0.3)
        protocol.delay(seconds=2)
        p20.dispense(ENZYME_VOL, r, rate=0.3)
        p20.mix(5, 12, r, rate=0.6)
        p20.blow_out(r.top(-2))
        p20.drop_tip()

    protocol.comment("Digests assembled in A1-A12. Seal, spin down and incubate at the enzyme's temperature.")
