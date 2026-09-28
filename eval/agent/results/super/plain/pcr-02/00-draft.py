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
    # assume samples in B1..B24? Actually we have 24 samples, place them in rack starting at B1
    for i in range(24):
        well = tuberack.wells()[i]  # gives all wells; we need skip A1,A2 used above
    # easier: assign manually
    # Let's list wells: A1..D6
    # We used A1, A2 for master mix and water. Samples start at A3.
    sample_wells = [f"A{3+i}" for i in range(24)]
    for i, well_name in enumerate(sample_wells):
        tuberack[well_name].load_liquid(liquid=samples[i], volume=50)

    # load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # helper to dispense component to all wells
    def dispense_all(source_well, volume):
        for col in range(1, 13):  # columns 1-12
            for row in range(8):  # rows A-H
                well_name = f"{chr(65+row)}{col}"
                if len([w for w in plate.wells() if w.well_name == well_name]) == 0:
                    continue
                if len([w for w in plate.wells() if w.well_name == well_name]) >= 24:
                    # stop after 24 wells (A1..D6? but we just fill first 24 in column order)
                    pass
        # simpler: iterate over first 24 wells of plate
    # Actually easier: get list of first 24 wells
    first_24 = plate.wells()[:24]
    p20.pick_up_tip()
    for well in first_24:
        p20.aspirate(12.5, tuberack["A1"])
        p20.dispense(12.5, well)
    p20.drop_tip()

    p20.pick_up_tip()
    for well in first_24:
        p20.aspirate(10.5, tuberack["A2"])
        p20.dispense(10.5, well)
    p20.drop_tip()

    p20.pick_up_tip()
    for i, well in enumerate(first_24):
        sample_well = tuberack[sample_wells[i]]
        p20.aspirate(2, sample_well)
        p20.dispense(2, well)
    p20.drop_tip()
