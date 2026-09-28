import json
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 25ul reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

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

    # load liquids into sources (starting volumes)
    tuberack["A1"].load_liquid(liquid=master_mix, volume=500)  # master mix tube
    tuberack["A2"].load_liquid(liquid=water, volume=500)      # water tube

    # assign sample wells: all wells except A1 and A2
    all_wells = [well for well in tuberack.wells()]
    sample_wells = [w for w in all_wells if w.well_name not in ("A1", "A2")]
    assert len(sample_wells) >= 24, "Not enough wells for samples"
    for i, liq in enumerate(samples):
        sample_wells[i].load_liquid(liquid=liq, volume=50)

    # load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # first 24 wells of plate in column order (A1..A12, B1..B12, ...)
    first_24 = plate.wells()[:24]

    # add master mix
    p20.pick_up_tip()
    for well in first_24:
        p20.aspirate(12.5, tuberack["A1"])
        p20.dispense(12.5, well)
    p20.drop_tip()

    # add water
    p20.pick_up_tip()
    for well in first_24:
        p20.aspirate(10.5, tuberack["A2"])
        p20.dispense(10.5, well)
    p20.drop_tip()

    # add samples
    p20.pick_up_tip()
    for i, well in enumerate(first_24):
        p20.aspirate(2, sample_wells[i])
        p20.dispense(2, well)
    p20.drop_tip()
