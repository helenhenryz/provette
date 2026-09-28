from opentrons import protocol_api

metadata = {
    "protocolName": "12 Restriction Digests (20 ul each)",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Temperature module (keep reagents at 4°C) -----
    temp_mod = protocol.load_module("temperature module gen2", 1)
    # Only aluminium blocks may be loaded on a temperature module
    temp_block = temp_mod.load_labware(
        "opentrons_24_aluminumblock_nest_1.5ml_snapcap"
    )
    # Set temperature before any aspiration from the block
    temp_mod.set_temperature(4)

    # ----- Labware -----
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 2)   # for p20
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 3                 # PCR plate
    )

    # ----- Pipette -----
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tips20]
    )

    # ----- Define liquids -----
    water = protocol.define_liquid(
        name="water", description="nuclease‑free water", display_color="#FFFFFF"
    )
    buffer = protocol.define_liquid(
        name="buffer", description="10× restriction buffer", display_color="#0000FF"
    )
    enzyme = protocol.define_liquid(
        name="enzyme", description="Restriction enzyme", display_color="#FF0000"
    )
    plasmid_liquids = [
        protocol.define_liquid(
            name=f"plasmid {i}",
            description=f"Plasmid {i} DNA",
            display_color="#00FF00"
        )
        for i in range(1, 13)
    ]

    # ----- Load liquids into the temperature‑block tubes -----
    # Water, buffer, enzyme in column 1 (rows A‑C)
    temp_block["A1"].load_liquid(liquid=water, volume=200)   # ~200 µL water
    temp_block["A2"].load_liquid(liquid=buffer, volume=100)  # ~100 µL buffer
    temp_block["A3"].load_liquid(liquid=enzyme, volume=100)  # ~100 µL enzyme

    # Plasmid sources: column 2, rows A‑L (A2 … L2)
    rows = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
    for i, row in enumerate(rows):
        temp_block[f"{row}2"].load_liquid(
            liquid=plasmid_liquids[i],
            volume=100   # ~100 µL each plasmid source
        )

    # Destination wells for the 12 reactions: column 1, rows A‑L (A1 … L1) on the plate
    reaction_wells = [plate[f"{row}1"] for row in rows]

    # ----- Helper: blow out to keep tip empty -----
    def safe_aspirate(disp_vol, source):
        p20.aspirate(disp_vol, source)
        p20.blow_out()   # ensure tip is empty after dispense later

    # ----- 1. Water (12 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        safe_aspirate(12, temp_block["A1"])
        p20.dispense(12, well)
    p20.drop_tip()

    # ----- 2. Buffer (2 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        safe_aspirate(2, temp_block["A2"])
        p20.dispense(2, well)
    p20.drop_tip()

    # ----- 3. Enzyme (1 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        safe_aspirate(1, temp_block["A3"])
        p20.dispense(1, well)
    p20.drop_tip()

    # ----- 4. Plasmid addition (5 µL each) + mix -----
    for idx, well in enumerate(reaction_wells):
        p20.pick_up_tip()
        # aspirate the specific plasmid
        safe_aspirate(5, temp_block[f"{rows[idx]}2"])
        p20.dispense(5, well)
        # mix after the last addition to avoid the “last addition not mixed” warning
        # 3 strokes of 15 µL each (< full well volume, total ≈ 2 wells’ worth)
        p20.mix(3, 15, well)
        p20.drop_tip()

    # No further steps required; the reaction mix is ready in the plate.
