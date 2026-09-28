metadata = {
    "protocolName": "PCR assembly from separate components",
    "apiLevel": "2.19",
}
# Optional: explicit requirements compatibility comment
# To run: opentrons_simulate 00-one-shot.py

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
    sample_liquids = {}
    for i in range(1, 13):
        name = f"sample {i}"
        liq = protocol.define_liquid(
            name=name,
            description=f"Template DNA sample {i}",
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

    # Load initial volumes onto the cold block (tube rack format)
    # Samples in positions A1-A12
    for i in range(1, 13):
        block[f"A{i}"].load_liquid(
            liquid=sample_liquids[f"sample {i}"], volume=500.0
        )

    # Source stocks for reagents (positions B1-B5)
    block["B1"].load_liquid(liquid=buffer_liq, volume=500.0)      # buffer
    block["B2"].load_liquid(liquid=polymerase_liq, volume=200.0)  # polymerase
    block["B3"].load_liquid(liquid=fwd_primer_liq, volume=200.0)  # fwd primer
    block["B4"].load_liquid(liquid=rev_primer_liq, volume=200.0)  # rev primer
    block["B5"].load_liquid(liquid=water_liq, volume=500.0)       # water
    # Position B6 will receive the prepared master mix (initially empty)

    # ------------- Prepare Master Mix (one tip per reagent) ------------
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

    # ------------- Distribute Master Mix to Plate (23 µL per well) ----------
    for col in range(1, 13):
        dest_well = plate[f"A{col}"]
        p20.pick_up_tip()
        p20.aspirate(23.0, mastermix_well)
        p20.dispense(23.0, dest_well)
        p20.drop_tip()

    # ------------- Add Template (2 µL per sample) --------------------------
    for col in range(1, 13):
        src_well = block[f"A{col}"]
        dest_well = plate[f"A{col}"]
        p20.pick_up_tip()
        p20.aspirate(2.0, src_well)
        p20.dispense(2.0, dest_well)
        p20.drop_tip()
    # End of protocol
