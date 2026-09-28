from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_24",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    samples_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    master_mix_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="2x PCR master mix with primers", display_color="#FF0000"
    )
    water = protocol.define_liquid(
        name="water", description="nuclease-free water", display_color="#0000FF"
    )
    samples = {}
    for i in range(1, 25):
        samples[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color=f"#{i:06X}"
        )

    # Load liquids into source wells
    master_mix_rack["A1"].load_liquid(liquid=master_mix, volume=200)
    water_reservoir["A1"].load_liquid(liquid=water, volume=1000)

    # Define target wells: A1-A6, B1-B6, C1-C6, D1-D6 (24 wells)
    target_wells = []
    for col in ["A", "B", "C", "D"]:
        for row in range(1, 7):
            target_wells.append(col + str(row))

    # Load samples into sample rack wells matching target_wells order
    for i in range(24):
        well_label = target_wells[i]
        samples_rack[well_label].load_liquid(liquid=samples[f"sample {i+1}"], volume=10)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Transfer for each of the 24 reactions
    for i in range(24):
        p20.pick_up_tip()
        # Add 12.5 ul master mix
        p20.aspirate(12.5, master_mix_rack["A1"])
        p20.dispense(12.5, plate[target_wells[i]])
        # Add 10.5 ul water
        p20.aspirate(10.5, water_reservoir["A1"])
        p20.dispense(10.5, plate[target_wells[i]])
        # Add 2 ul sample
        p20.aspirate(2, samples_rack[target_wells[i]])
        p20.dispense(2, plate[target_wells[i]])
        p20.drop_tip()
