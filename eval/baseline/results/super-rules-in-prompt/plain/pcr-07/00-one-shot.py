metadata = {
    "protocolName": "PCR assembly from separate components",
    "apiLevel": "2.19",
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

    # ----- Pipette -----
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # ----- Liquids -----
    # Samples
    sample_liquids = {}
    for i in range(1, 13):
        name = f"sample {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"Template DNA sample {i}",
            display_color="#FF0000",  # arbitrary colour
        )
        sample_liquids[name] = liq

    # Other reagents
    polymerase_liq = protocol.define_liquid(
        name="polymerase",
        description="Taq polymerase",
        display_color="#00FF00",
    )
    fwd_primer_liq = protocol.define_liquid(
        name="fwd primer",
        description="Forward primer",
        display_color="#0000FF",
    )
    rev_primer_liq = protocol.define_liquid(
        name="rev primer",
        description="Reverse primer",
        display_color="#00FF00",
    )
    water_liq = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#FFFFFF",
    )
    buffer_liq = protocol.define_liquid(
        name="buffer",
        description="PCR buffer mix",
        display_color="#FFFF00",
    )

    # Load liquids into the cold block
    # Samples in columns A1‑A12
    for i in range(1, 13):
        block[f"A{i}"].load_liquid(
            liquid=sample_liquids[f"sample {i}"], volume=500.0
        )

    # Reagents (source stocks) in B1‑B5
    block["B1"].load_liquid(liquid=buffer_liq, volume=500.0)      # buffer
    block["B2"].load_liquid(liquid=polymerase_liq, volume=200.0)  # polymerase
    block["B3"].load_liquid(liquid=fwd_primer_liq, volume=200.0)  # fwd primer
    block["B4"].load_liquid(liquid=rev_primer_liq, volume=200.0)  # rev primer
    block["B5"].load_liquid(liquid=water_liq, volume=500.0)       # water
    # B6 will be used for the master mix (starts empty)

    # ----- Master mix preparation (one tip per reagent) -----
    mastermix_well = block["B6"]
    reagent_map = {
        "buffer": ("B1", buffer_liq, 10.0 * 12),          # 120 µL
        "polymerase": ("B2", polymerase_liq, 0.5 * 12),   # 6 µL
        "fwd primer": ("B3", fwd_primer_liq, 1.0 * 12),   # 12 µL
        "rev primer": ("B4", rev_primer_liq, 1.0 * 12),   # 12 µL
        "water": ("B5", water_liq, 10.5 * 12),            # 126 µL
    }

    for loc, liq, vol in reagent_map.values():
        source = block[loc]
        p20.pick_up_tip()
        p20.aspirate(vol, source)
        p20.dispense(vol, mastermix_well)
        p20.drop_tip()

    # ----- Distribute master mix to PCR plate (23 µL per well) -----
    for col in range(1, 13):
        dest_well = plate[f"A{col}"]
        p20.pick_up_tip()
        p20.aspirate(23.0, mastermix_well)
        p20.dispense(23.0, dest_well)
        p20.drop_tip()

    # ----- Add template (sample) --- 2 µL per well -----
    for col in range(1, 13):
        src_well = block[f"A{col}"]
        dest_well = plate[f"A{col}"]
        p20.pick_up_tip()
        p20.aspirate(2.0, src_well)
        p20.dispense(2.0, dest_well)
        p20.drop_tip()
    # Protocol finished
