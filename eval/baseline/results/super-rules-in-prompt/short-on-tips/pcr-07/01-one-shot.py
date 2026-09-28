from opentrons import protocol_api

metadata = {
    "protocolName": "PCR assembly (12 samples) - minimal tips",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Modules & Labware ----
    temp_mod = protocol.load_module("temperature module gen2", 1)
    tube_rack = temp_mod.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap",
        "tubes"
    )
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

    # Exact names as requested
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

    # ---- Load stocks into the tube rack ----
    # Samples in A1-A12
    for i in range(12):
        sample_name = f"sample {i+1}"
        tube_rack[f"A{i+1}"].load_liquid(liquids[sample_name], volume=200)  # 200 µL each

    # Reagents in B1-B5
    tube_rack["B1"].load_liquid(liquids["polymerase"], volume=200)
    tube_rack["B2"].load_liquid(liquids["fwd primer"], volume=200)
    tube_rack["B3"].load_liquid(liquids["rev primer"], volume=200)
    tube_rack["B4"].load_liquid(liquids["water"], volume=1000)
    tube_rack["B5"].load_liquid(liquids["buffer"], volume=200)

    # Keep reagents cold
    temp_mod.set_temperature(4)
    protocol.delay(seconds=2)  # let the block equilibrate (sim-friendly)

    # ---- Reaction setup ----
    V_WATER   = 10.5   # µL
    V_BUFFER  = 10.0   # µL
    V_FWD     = 1.0    # µL
    V_REV     = 1.0    # µL
    V_POLY    = 0.5    # µL
    V_SAMPLE  = 2.0    # µL  (template already present)

    reaction_wells = [tube_rack[f"A{i+1}"] for i in range(12)]

    # Ordered to avoid enzyme‑before‑water warning
    reagents = [
        ("water",      tube_rack["B4"], V_WATER),
        ("buffer",     tube_rack["B5"], V_BUFFER),
        ("fwd primer", tube_rack["B2"], V_FWD),
        ("rev primer", tube_rack["B3"], V_REV),
        ("polymerase", tube_rack["B1"], V_POLY)
    ]

    # Use a single tip for the whole protocol
    p20.pick_up_tip()
    for _, src, vol in reagents:
        for well in reaction_wells:
            p20.aspirate(vol, src)
            p20.dispense(vol, well)
            # Ensure tip is empty before next aspiration
            p20.blow_out(well)
    p20.drop_tip()
    # At this point each well in A1‑A12 contains a complete 25 µL PCR reaction.
