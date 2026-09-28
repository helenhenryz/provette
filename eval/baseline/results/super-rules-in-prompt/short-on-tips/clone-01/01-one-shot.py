from opentrons import protocol_api

metadata = {
    "protocolName": "12 Restriction Digests (20 ul each)",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Temperature module (keep reagents at 4°C) ----
    temp_mod = protocol.load_module("temperature module gen2", 1)
    # Only aluminum blocks may be placed on a temperature module
    temp_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    temp_mod.set_temperature(4)          # set before any aspiration

    # ---- Labware ----
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 2)   # for p20
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 3                 # PCR plate
    )

    # ---- Pipette ----
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tips20]
    )

    # ---- Define liquids ----
    water = protocol.define_liquid(
        name="water", description="nuclease‑free water", display_color="#FFFFFF"
    )
    buffer = protocol.define_liquid(
        name="buffer", description="10× restriction buffer", display_color="#0000FF"
    )
    enzyme = protocol.define_liquid(
        name="enzyme", description="Restriction enzyme", display_color="#FF0000"
    )
    plasmid_defs = [
        protocol.define_liquid(
            name=f"plasmid {i}",
            description=f"Plasmid {i} DNA",
            display_color="#00FF00"
        )
        for i in range(1, 13)
    ]

    # ---- Load reagents onto the temperature block ----
    # Column 1: water, buffer, enzyme
    temp_block["A1"].load_liquid(liquid=water, volume=200)   # ~200 µL water
    temp_block["A2"].load_liquid(liquid=buffer, volume=100)  # ~100 µL buffer
    temp_block["A3"].load_liquid(liquid=enzyme, volume=100)  # ~100 µL enzyme

    # Plasmids: column 2, rows A–L (A2 … L2)
    rows = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    for letter, plasm in zip(rows, plasmid_defs):
        temp_block[f"{letter}2"].load_liquid(liquid=plasm, volume=100)

    # Destination wells for reactions: column 1, rows A–L on the PCR plate
    reaction_wells = [plate[f"{letter}1"] for letter in rows]

    # Helper to aspirate and then blow out (keeps tip empty for next dispense)
    def aspirate_and_empty(volume, source):
        p20.aspirate(volume, source)
        p20.blow_out()

    # ---- 1. Water (12 µL per well) ----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(12, temp_block["A1"])
        p20.dispense(12, well)
    p20.drop_tip()

    # ---- 2. Buffer (2 µL per well) ----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(2, temp_block["A2"])
        p20.dispense(2, well)
    p20.drop_tip()

    # ---- 3. Enzyme (1 µL per well) ----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(1, temp_block["A3"])
        p20.dispense(1, well)
    p20.drop_tip()

    # ---- 4. Plasmid (5 µL each) + mix ----
    for idx, letter in enumerate(rows):
        p20.pick_up_tip()
        src_well = temp_block[f"{letter}2"]
        aspirate_and_empty(5, src_well)
        p20.dispense(5, reaction_wells[idx])
        # Mix after the last addition to satisfy the "last addition not mixed" rule.
        # 3 strokes of 15 µL each (< full well volume) → acceptable mixing.
        p20.mix(3, 15, reaction_wells[idx])
        p20.drop_tip()

    # Reaction mix (20 µL) is now in plate wells A1–L1.
