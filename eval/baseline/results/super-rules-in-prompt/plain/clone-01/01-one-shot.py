from opentrons import protocol_api

metadata = {
    "protocolName": "Setup 12 Restriction Digests",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Module & Labware ----------
    temp_mod = protocol.load_module("temperature module gen2", 1)
    temp_mod.set_temperature(4)                   # Keep reagents cold

    # Aluminium block that holds 1.5 ml snap‑cap tubes (co‑located with tip racks/plates)
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
    # Plasmid liquids (one distinct liquid per plasmid)
    plasmid_names = [f"plasmid {i}" for i in range(1, 13)]
    plasmid_liquids = {}
    for name in plasmid_names:
        liq = protocol.define_liquid(
            name=name,
            description=f"Plasmid DNA {name.split()[-1]}",
            display_color="#%06x" % ((hash(name) % 0xFFFFFF))
        )
        plasmid_liquids[name] = liq

    water = protocol.define_liquid(
        name="water",
        description="Nuclease‑free water",
        display_color="#0000FF"
    )
    buffer = protocol.define_liquid(
        name="buffer",
        description="10× reaction buffer",
        display_color="#00FF00"
    )
    enzyme = protocol.define_liquid(
        name="enzyme",
        description="Restriction enzyme",
        display_color="#FF0000"
    )

    # ---------- Load initial liquids ----------
    # Plasmids occupy positions A1–A6 and B1–B6 on the aluminium block
    plasmid_positions = [
        "A1", "A2", "A3", "A4", "A5", "A6",
        "B1", "B2", "B3", "B4", "B5", "B6"
    ]

    for pos, name in zip(plasmid_positions, plasmid_names):
        tuberack[pos].load_liquid(plasmid_liquids[name], volume=500)  # µL

    # Buffer, enzyme, water in column C (any free spots)
    tuberack["C1"].load_liquid(buffer, volume=1000)   # µL
    tuberack["C2"].load_liquid(enzyme, volume=500)    # µL
    tuberack["C3"].load_liquid(water, volume=1000)    # µL

    # Destination wells – first 12 wells of the PCR plate (row A)
    reaction_wells = pcr_plate.rows()[0][:12]

    # Helper: transfer a volume from a source well to several destinations,
    # using a fresh tip for each transfer (avoids carry‑over).
    def transfer(volume, source_well, destinations):
        for dest in destinations:
            p20.pick_up_tip()
            p20.aspirate(volume, source_well)
            p20.dispense(volume, dest)
            p20.drop_tip()

    # ---------- Protocol steps ----------
    # 1) Water (12 µL per reaction)
    transfer(12, tuberack["C3"], reaction_wells)

    # 2) Buffer (2 µL per reaction)
    transfer(2, tuberack["C1"], reaction_wells)

    # 3) Enzyme (1 µL per reaction)
    transfer(1, tuberack["C2"], reaction_wells)

    # 4) Plasmids – 5 µL each, unique plasmid per well
    for src_pos, dest_well in zip(plasmid_positions, reaction_wells):
        p20.pick_up_tip()
        p20.aspirate(5, tuberack[src_pos])
        p20.dispense(5, dest_well)
        p20.drop_tip()
