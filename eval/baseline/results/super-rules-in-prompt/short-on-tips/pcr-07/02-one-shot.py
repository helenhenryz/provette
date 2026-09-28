from opentrons import protocol_api

metadata = {
    "protocolName": "PCR assembly (12 samples) - minimal tips",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Modules & Labware ----
    # Temperature module to keep reagents cold
    temp_mod = protocol.load_module("temperature module gen2", 1)
    # Aluminium block compatible with temperature module (holds 1.5 ml tubes)
    tube_block = temp_mod.load_labware(
        "opentrons_24_aluminumblock_nest_1.5ml_snapcap",
        "tubes"
    )
    # Single tip rack for the p20
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)

    # ---- Pipette ----
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # ---- Liquid definitions (store the Liquid objects) ----
    liquids = {}
    def add_liquid(name, color):
        liq = protocol.define_liquid(
            name=name,
            description=f"{name} stock",
            display_color=color
        )
        liquids[name] = liq

    # Exact names as required
    add_liquid("sample 1", "#FF0000")
    add_liquid("sample 2", "#00FF00")
    add_liquid("sample 3", "#0000FF")
    add_liquid("sample 4", "#FFFF00")
    add_liquid("sample 5", "#FF00FF")
    add_liquid("sample 6", "#00FFFF")
    add_liquid("sample 7", "#800000")
    add_liquid("sample 8", "#008000")
    add_liquid("sample 9", "#000080")
    add_liquid("sample 10", "#808000")
    add_liquid("sample 11", "#800080")
    add_liquid("sample 12", "#008080")
    add_liquid("polymerase", "#FFFFFF")
    add_liquid("fwd primer", "#FFA500")
    add_liquid("rev primer", "#800080")
    add_liquid("water", "#00BFFF")
    add_liquid("buffer", "#32CD32")

    # ---- Load stocks into the aluminium block ----
    # Samples in A1‑A12 (template)
    for i in range(12):
        sample_name = f"sample {i+1}"
        tube_block[f"A{i+1}"].load_liquid(liquids[sample_name], volume=200)  # 200 µL each

    # Reagents in B1‑B5
    tube_block["B1"].load_liquid(liquids["polymerase"], volume=200)
    tube_block["B2"].load_liquid(liquids["fwd primer"], volume=200)
    tube_block["B3"].load_liquid(liquids["rev primer"], volume=200)
    tube_block["B4"].load_liquid(liquids["water"], volume=1000)
    tube_block["B5"].load_liquid(liquids["buffer"], volume=200)

    # Keep reagents cold
    temp_mod.set_temperature(4)
    protocol.delay(seconds=2)  # allow block to equilibrate (sim‑friendly)

    # ---- Reaction setup ----
    V_WATER   = 10.5   # µL
    V_BUFFER  = 10.0   # µL
    V_FWD     = 1.0    # µL
    V_REV     = 1.0    # µL
    V_POLY    = 0.5    # µL
    # V_SAMPLE (template) is already present in the tube (2 µL needed);
    # we do not transfer it.

    reaction_wells = [tube_block[f"A{i+1}"] for i in range(12)]

    # Order chosen to avoid “enzyme added before water” warnings
    reagents = [
        ("water",      tube_block["B4"], V_WATER),
        ("buffer",     tube_block["B5"], V_BUFFER),
        ("fwd primer", tube_block["B2"], V_FWD),
        ("rev primer", tube_block["B3"], V_REV),
        ("polymerase", tube_block["B1"], V_POLY)
    ]

    # Use a single tip for the whole protocol (minimises tip usage)
    p20.pick_up_tip()
    for _, src_vol in reagents:
        src, vol = src_vol
        for well in reaction_wells:
            p20.aspirate(vol, src)
            p20.dispense(vol, well)
            # Ensure tip is empty before next aspiration to avoid carry‑over
            p20.blow_out(well)
    p20.drop_tip()
    # At this point each well in A1‑A12 contains a complete 25 µL PCR reaction.
