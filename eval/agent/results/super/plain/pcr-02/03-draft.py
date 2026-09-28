import json
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 25ul reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack_mm = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)  # master mix & water
    tuberack_samples = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)  # 24 samples
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="2x PCR master mix with primers",
        display_color="#FF0000",
    )
    water = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#0000FF",
    )
    samples = []
    for i in range(1, 25):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Genomic DNA sample {i}",
            display_color="#00FF00",
        )
        samples.append(liq)

    # load liquids into sources
    tuberack_mm["A1"].load_liquid(liquid=master_mix, volume=500)  # master mix
    tuberack_mm["A2"].load_liquid(liquid=water, volume=500)      # water

    # load samples into tuberack_samples wells A1..A24 (column order)
    for i, liq in enumerate(samples):
        well = tuberack_samples.wells()[i]  # gives wells in order A1..A24
        well.load_liquid(liquid=liq, volume=50)

    # load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # first 24 wells of plate in column order (A1..A12, B1..B12, ...)
    first_24 = plate.wells()[:24]

    for i, well in enumerate(first_24):
        p20.pick_up_tip()
        # master mix
        p20.aspirate(12.5, tuberack_mm["A1"])
        p20.dispense(12.5, well)
        # water
        p20.aspirate(10.5, tuberack_mm["A2"])
        p20.dispense(10.5, well)
        # sample
        samp_well = tuberack_samples.wells()[i]
        p20.aspirate(2, samp_well)
        p20.dispense(2, well)
        # mix
        p20.mix(5, 15, well)  # 5 cycles of 15 ul
        p20.drop_tip()
