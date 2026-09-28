metadata = {
    "protocolName": "96-well PCR master mix + template addition",
    "apiLevel": "2.19"
}

def run(protocol):
    # ---- Labware ---------------------------------------------------------
    # Tuberack holding the master‑mix tube (2 mL snapcap)
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_2ml_snapcap", 1
    )
    # 20 µL tip rack (used for both master‑mix and template steps)
    tiprack = protocol.load_labware(
        "opentrons_96_tiprack_20ul", 2
    )
    # Sample plate (source of template DNA)
    sample_plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat", 3
    )
    # Destination PCR plate
    pcr_plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 4
    )

    # ---- Pipettes --------------------------------------------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # ---- Liquids ---------------------------------------------------------
    # Master mix (must be exactly this name)
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FFA500"
    )
    # Place master mix in the tuberack well A1 (≈2 mL)
    tuberack["A1"].load_liquid(liquid=master_mix, volume=2000)

    # Define a unique liquid for each sample well and load 2 µL
    for col in "ABCDEFGH":
        for row in range(1, 13):
            well = f"{col}{row}"
            liq = protocol.define_liquid(
                name=f"sample_{well}",
                description="template DNA",
                display_color="#{:06x}".format(((ord(col) - 65) * 12 + (row - 1)) % 0xFFFFFF)
            )
            sample_plate[well].load_liquid(liquid=liq, volume=20)

    # ---- Protocol ---------------------------------------------------------
    NEGATIVE_CONTROL = "H12"  # well that receives only master mix

    # 1. Add master mix (18 µL) to every well of the PCR plate
    p20.pick_up_tip()
    for column in pcr_plate.columns():
        for well in column:
            p20.aspirate(18, tuberack["A1"])
            p20.dispense(18, well)
    p20.drop_tip()

    # 2. Add template (2 µL) from each sample well to the matching PCR well,
    #    skipping the negative control well.
    for col in "ABCDEFGH":
        for row in range(1, 13):
            well = f"{col}{row}"
            if well == NEGATIVE_CONTROL:
                continue
            p20.pick_up_tip()
            p20.aspirate(2, sample_plate[well])
            p20.dispense(2, pcr_plate[well])
            p20.drop_tip()
