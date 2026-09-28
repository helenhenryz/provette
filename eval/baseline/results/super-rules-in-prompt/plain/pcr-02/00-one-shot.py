metadata = {
    "protocolName": "PCR setup: 24 genomic DNA samples → 25 µL reactions",
    "author": "",
    "description": "Aliquot master mix, water, and each DNA sample into a PCR plate to form 25 µL reactions.",
    "apiLevel": "2.19"
}

from opentrons import protocol_api


def run(protocol: protocol_api.ProtocolContext):
    # --- Labware --------------------------------------------------------------
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)          # tips for p20
    sample_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 2                       # DNA samples
    )
    reagent_rack = protocol.load_labware(
        "opentrons_24_tuberack_nest_1.5ml_snapcap", 3                     # master mix & water
    )
    plate = protocol.load_labware(
        "nest_96_wellplate_100ul_pcr_full_skirt", 4                        # PCR plate
    )

    # --- Pipette --------------------------------------------------------------
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # --- Liquids --------------------------------------------------------------
    # Define all distinct liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2× PCR master mix with primers",
        display_color="#FFAA00"
    )
    water = protocol.define_liquid(
        name="water",
        description="nuclease‑free water",
        display_color="#00AAFF"
    )
    sample_liquids = []
    for i in range(1, 25):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color="#FF0000"
        )
        sample_liquids.append(liq)

    # Load liquids onto deck
    # Reagent rack: first well = master mix, second = water
    mm_well = reagent_rack.wells()[0]
    water_well = reagent_rack.wells()[1]
    mm_well.load_liquid(liquid=master_mix, volume=500)   # µL
    water_well.load_liquid(liquid=water, volume=500)

    # Sample rack: each well gets one DNA sample
    for well, liq in zip(sample_rack.wells(), sample_liquids):
        well.load_liquid(liquid=liq, volume=50)         # µL each sample sufficient for 2 µL transfers

    # --- Transfer parameters ---------------------------------------------------
    MM_VOL = 12.5      # µL master mix per reaction
    WATER_VOL = 10.5   # µL water per reaction
    SAMPLE_VOL = 2.0   # µL DNA per reaction

    # Aliquot master mix and water to each well using fresh tips each time
    for dest in plate.wells():
        p20.transfer(MM_VOL, mm_well, dest, new_tip='always')
        p20.transfer(WATER_VOL, water_well, dest, new_tip='always')

    # Aliquot each DNA sample to its corresponding well
    for src_sample, dest_well in zip(sample_rack.wells(), plate.wells()):
        p20.transfer(SAMPLE_VOL, src_sample, dest_well, new_tip='always')
