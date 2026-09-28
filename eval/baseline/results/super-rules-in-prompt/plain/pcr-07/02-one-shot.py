metadata = {
    "protocolName": "PCR assembly from separate components",
    "apiLevel": "2.19",
}

from opentrons import protocol_api


def run(protocol: protocol_api.ProtocolContext):
    # -------------------- Labware --------------------
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

    # ------------------- Pipette -------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # ------------------- Liquids -------------------
    # Define sample liquids (one per sample)
    sample_names = [f"sample {i}" for i in range(1, 13)]
    sample_liquids = {}
    for name in sample_names:
        liq = protocol.define_liquid(
            name=name,
            description=f"Template DNA {name}",
            display_color="#FF0000",
        )
        sample_liquids[name] = liq

    # Define reagent liquids
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

    # Positions for the 12 samples in the 24-well aluminum block
    sample_positions = ["A1", "A2", "A3", "A4",
                        "B1", "B2", "B3", "B4",
                        "C1", "C2", "C3", "C4"]

    # Load sample liquids into the cold block
    for name, pos in zip(sample_names, sample_positions):
        block[pos].load_liquid(liquid=sample_liquids[name], volume=500.0)

    # Load reagent stocks (columns B1‑B5 of the block)
    block["B1"].load_liquid(liquid=buffer_liq, volume=500.0)      # buffer
    block["B2"].load_liquid(liquid=polymerase_liq, volume=200.0)  # polymerase
    block["B3"].load_liquid(liquid=fwd_primer_liq, volume=200.0)  # fwd primer
    block["B4"].load_liquid(liquid=rev_primer_liq, volume=200.0)  # rev primer
    block["B5"].load_liquid(liquid=water_liq, volume=500.0)       # water
    # Block position B6 will hold the prepared master mix

    # ------------- Prepare Master Mix (one tip per reagent) -------------
    mastermix_well = block["B6"]
    reagent_specs = [
        ("B1", buffer_liq, buffer_liq, 10.0 * 12),     # 120 µL
        ("B2", polymerase_liq, polymerase_liq, 0.5 * 12), # 6 µL
        ("B3", fwd_primer_liq, fwd_primer_liq, 1.0 * 12), # 12 µL
        ("B4", rev_primer_liq, rev_primer_liq, 1.0 * 12), # 12 µL
        ("B5", water_liq, water_liq, 10.5 * 12),        # 126 µL
    ]

    for src_loc, liq_def, _, vol in reagent_specs:
        source = block[src_loc]
        p20.pick_up_tip()
        p20.aspirate(vol, source)
        p20.dispense(vol, mastermix_well)
        p20.drop_tip()

    # ------------- Distribute Master Mix to Plate (23 µL per well) ------
    for col in range(1, 13):  # wells A1‑A12
        dest_well = plate[f"A{col}"]
        p20.pick_up_tip()
        p20.aspirate(23.0, mastermix_well)
        p20.dispense(23.0, dest_well)
        p20.drop_tip()

    # ------------- Add Template (2 µL per sample) -----------------------
    for idx, pos in enumerate(sample_positions, start=1):  # idx = 1..12
        src_well = block[pos]
        dest_well = plate[f"A{idx}"]
        p20.pick_up_tip()
        p20.aspirate(2.0, src_well)
        p20.dispense(2.0, dest_well)
        p20.drop_tip()
    # End of protocol
