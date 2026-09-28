from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 2)
    samples = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    master_mix_tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_racks])

    # Define liquids
    protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#0000FF")
    for i in range(1, 25):
        protocol.define_liquid(name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color=f"#{i:06X}")

    # Load liquids into source wells
    master_mix_tubes["A1"].load_liquid(liquid="master mix", volume=500)
    water_reservoir["A1"].load_liquid(liquid="water", volume=1000)
    for i in range(1, 25):
        col_idx = (i-1) // 6
        row_idx = (i-1) % 6 + 1
        col_letter = ["A", "B", "C", "D"][col_idx]
        well_name = f"{col_letter}{row_idx}"
        samples[well_name].load_liquid(liquid=f"sample {i}", volume=10)

    # Destination well order: A1-A12, B1-B12
    dest_wells = []
    for col in ["A", "B"]:
        for row in range(1, 13):
            dest_wells.append(f"{col}{row}")

    # Pick up tip and set up transfers
    p20.pick_up_tip()
    for i in range(24):
        dest_well = plate[dest_wells[i]]
        # Add 12.5 ul master mix
        p20.aspirate(12.5, master_mix_tubes["A1"])
        p20.dispense(12.5, dest_well)
        # Add 10.5 ul water
        p20.aspirate(10.5, water_reservoir["A1"])
        p20.dispense(10.5, dest_well)
        # Determine sample well name
        col_idx = i // 6
        row_idx = i % 6 + 1
        col_letter = ["A", "B", "C", "D"][col_idx]
        sample_well_name = f"{col_letter}{row_idx}"
        # Add 2 ul sample
        p20.aspirate(2, samples[sample_well_name])
        p20.dispense(2, dest_well)
    # Drop tip
    p20.drop_tip()
