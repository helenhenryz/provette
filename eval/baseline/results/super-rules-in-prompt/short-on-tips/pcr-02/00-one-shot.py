from opentrons import protocol_api

metadata = {
    "protocolName": "PCR reaction setup (24 samples)",
    "apiLevel": "2.19",
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- liquid definitions -----
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2x PCR master mix with primers",
        display_color="#FFFF00",
    )
    water = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#00FFFF",
    )
    sample_liquids = []
    for i in range(1, 26):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color=f"#FF{((i*7) % 256):02x}00",  # distinct colors
        )
        sample_liquids.append(liq)

    # ----- labware -----
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)          # for p20
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 2
    )                                                                        # holds 24 samples
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 3
    )                                                                        # PCR plate
    reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml", 4
    )                                                                        # master mix & water

    # ----- pipette -----
    p20 = protocol.load_instrument(
        "p20_single_gen2", "right", tip_racks=[tiprack]
    )

    # ----- load liquids -----
    # master mix and water in reservoir wells A1 and A2
    reservoir["A1"].load_liquid(liquid=master_mix, volume=500)   # µL
    reservoir["A2"].load_liquid(liquid=water, volume=500)

    # 24 DNA samples in tuberack (each well gets its own sample)
    for well, liq in zip(tuberack.wells(), sample_liquids):
        well.load_liquid(liquid=liq, volume=20)   # µL per sample tube

    # ----- protocol steps -----
    # 1. Master mix (12.5 µL)
    p20.pick_up_tip()
    for src, dest in zip(tuberack.wells(), plate.wells()):
        p20.aspirate(12.5, reservoir["A1"])
        p20.dispense(12.5, dest)
        p20.blow_out(dest)   # clear tip to avoid carry‑over
    p20.drop_tip()

    # 2. Water (10.5 µL)
    p20.pick_up_tip()
    for src, dest in zip(tuberack.wells(), plate.wells()):
        p20.aspirate(10.5, reservoir["A2"])
        p20.dispense(10.5, dest)
        p20.blow_out(dest)
    p20.drop_tip()

    # 3. DNA sample (2 µL)
    p20.pick_up_tip()
    for src, dest in zip(tuberack.wells(), plate.wells()):
        p20.aspirate(2, src)
        p20.dispense(2, dest)
        p20.blow_out(dest)
    p20.drop_tip()
