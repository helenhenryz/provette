from opentrons import protocol_api

metadata = {
    "protocolName": "12 Restriction Digests (20 ul each)",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Temperature module (keep reagents at 4°C) -----
    temp_mod = protocol.load_module("temperature module gen2", 1)
    # Only aluminium blocks may be placed on a temperature module
    temp_block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    temp_mod.set_temperature(4)          # set before any aspiration

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
    plasmid_defs = [
        protocol.define_liquid(
            name=f"plasmid {i}",
            description=f"Plasmid {i} DNA",
            display_color="#00FF00"
        )
        for i in range(1, 13)
    ]

    # ----- Generate well list for the aluminium block (column‑major order) -----
    rows = ['A', 'B', 'C', 'D']
    cols = range(1, 7)                     # columns 1‑6
    block_wells = [f"{r}{c}" for c in cols for r in rows]   # A1,B1,C1,D1, A2,...
    # Assign specific wells
    water_well   = block_wells[0]   # A1
    buffer_well  = block_wells[1]   # B1
    enzyme_well  = block_wells[2]   # C1
    plasmid_wells = block_wells[3:15]   # next 12 wells: D1, A2, B2, C2, D2, A3, B3, C3, D3, A4, B4, C4

    # ----- Load reagents onto the temperature block -----
    temp_block[water_well].load_liquid(liquid=water, volume=200)   # ~200 µL water
    temp_block[buffer_well].load_liquid(liquid=buffer, volume=100) # ~100 µL buffer
    temp_block[enzyme_well].load_liquid(liquid=enzyme, volume=100) # ~100 µL enzyme
    for well, plasm in zip(plasmid_wells, plasmid_defs):
        temp_block[well].load_liquid(liquid=plasm, volume=100)     # ~100 µL each plasmid

    # Destination wells for the 12 reactions: column 1, rows A‑L on the PCR plate
    reaction_rows = ['A','B','C','D','E','F','G','H','I','J','K','L']
    reaction_wells = [plate[f"{r}1"] for r in reaction_rows]

    # Helper to aspirate and then blow out (keeps tip empty for next dispense)
    def aspirate_and_empty(vol, source):
        p20.aspirate(vol, source)
        p20.blow_out()

    # ----- 1. Water (12 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(12, temp_block[water_well])
        p20.dispense(12, well)
    p20.drop_tip()

    # ----- 2. Buffer (2 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(2, temp_block[buffer_well])
        p20.dispense(2, well)
    p20.drop_tip()

    # ----- 3. Enzyme (1 µL per well) -----
    p20.pick_up_tip()
    for well in reaction_wells:
        aspirate_and_empty(1, temp_block[enzyme_well])
        p20.dispense(1, well)
    p20.drop_tip()

    # ----- 4. Plasmid (5 µL each) + mix -----
    for idx, well in enumerate(reaction_wells):
        p20.pick_up_tip()
        src = temp_block[plasmid_wells[idx]]
        aspirate_and_empty(5, src)
        p20.dispense(5, well)
        # Mix after the last addition: 3 strokes of 15 µL each (< full well volume)
        p20.mix(3, 15, well)
        p20.drop_tip()

    # Reaction mix (20 µL) is now in plate wells A1–L1.
