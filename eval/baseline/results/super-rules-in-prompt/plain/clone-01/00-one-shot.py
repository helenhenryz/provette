from opentrons import protocol_api

metadata = {
    "protocolName": "Setup 12 Restriction Digests",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Modules & Labware ----------
    temp_mod = protocol.load_module("temperature module gen2", 1)
    temp_mod.set_temperature(4)               # keep reagents cold

    tuberack = temp_mod.load_labware(
        "opentrons_24_aluminumblock_nest_1.5ml_snapcap"
    )
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    pcr_plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 3
    )

    # ---------- Pipette ----------
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tiprack]
    )

    # ---------- Define liquids ----------
    # Plasmids
    plasmid_names = [f"plasmid {i}" for i in range(1, 13)]
    plasmid_liquids = {}
    plasmid_wells = []                     # physical wells holding each plasmid
    for i, name in enumerate(plasmid_names, start=1):
        liq = protocol.define_liquid(
            name=name,
            description=f"Plasmid DNA {i}",
            display_color="#%06x" % ((i * 0x123456) % 0xFFFFFF)
        )
        plasmid_liquids[name] = liq
        plasmid_wells.append(tuberack[f"A{i}"])

    water = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#0000FF"
    )
    buffer = protocol.define_liquid(
        name="buffer",
        description="10x reaction buffer",
        display_color="#00FF00"
    )
    enzyme = protocol.define_liquid(
        name="enzyme",
        description="Restriction enzyme",
        display_color="#FF0000"
    )

    # ---------- Load liquids into tubes ----------
    # Plasmids in column A (A1‑A12)
    for well, liq in zip(plasmid_wells, plasmid_liquids.values()):
        well.load_liquid(liq, volume=500)   # µL

    # Buffer, enzyme, water in column B
    tuberack["B1"].load_liquid(buffer, volume=1000)
    tuberack["B2"].load_liquid(enzyme, volume=500)
    tuberack["B3"].load_liquid(water, volume=1000)

    # Destination wells – first 12 wells of row A in the PCR plate
    reaction_wells = pcr_plate.rows()[0][:12]

    # Helper: dispense a volume from a source well to many destinations,
    # using a fresh tip for each transfer (to avoid cross‑contamination).
    def dispense(volume, source_well, destinations):
        for dest in destinations:
            p20.pick_up_tip()
            p20.aspirate(volume, source_well)
            p20.dispense(volume, dest)
            p20.drop_tip()

    # ---------- Protocol steps ----------
    # 1) Water (12 µL per reaction)
    dispense(12, tuberack["B3"], reaction_wells)

    # 2) Buffer (2 µL per reaction)
    dispense(2, tuberack["B1"], reaction_wells)

    # 3) Enzyme (1 µL per reaction)
    dispense(1, tuberack["B2"], reaction_wells)

    # 4) Plasmids – 5 µL each, unique plasmid per well
    for src_well, dest_well in zip(plasmid_wells, reaction_wells):
        p20.pick_up_tip()
        p20.aspirate(5, src_well)   # aspirate from the specific plasmid tube
        p20.dispense(5, dest_well)  # dispense into its reaction well
        p20.drop_tip()
