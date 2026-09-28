from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup for 8 samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    samples = {}
    for i in range(1, 9):
        samples[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color=f"#{i*100:03X}"
        )
    water = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#00FF00"
    )

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=master_mix, volume=200)
    tubes["A2"].load_liquid(liquid=samples["sample 1"], volume=10)
    tubes["A3"].load_liquid(liquid=samples["sample 2"], volume=10)
    tubes["A4"].load_liquid(liquid=samples["sample 3"], volume=10)
    tubes["A5"].load_liquid(liquid=samples["sample 4"], volume=10)
    tubes["B1"].load_liquid(liquid=samples["sample 5"], volume=10)
    tubes["B2"].load_liquid(liquid=samples["sample 6"], volume=10)
    tubes["B3"].load_liquid(liquid=samples["sample 7"], volume=10)
    tubes["B4"].load_liquid(liquid=samples["sample 8"], volume=10)
    tubes["B5"].load_liquid(liquid=water, volume=50)  # enough for NTC

    # Source wells for samples in order
    sample_source_wells = ["A2", "A3", "A4", "A5", "B1", "B2", "B3", "B4"]

    # Perform transfers for each of the 8 samples
    for i in range(1, 9):
        # Master mix transfer
        p20.pick_up_tip()
        p20.aspirate(20, tubes["A1"])
        dest_well = plate[f"A{i}"]
        p20.dispense(20, dest_well)
        p20.drop_tip()
        # Sample transfer
        p20.pick_up_tip()
        source_well_name = sample_source_wells[i-1]
        p20.aspirate(5, tubes[source_well_name])
        p20.dispense(5, dest_well)
        # Mix
        p20.mix(20, 5, dest_well)
        # Drop tip
        p20.drop_tip()

    # No‑template control (20 µL master mix + 5 µL water)
    p20.pick_up_tip()
    p20.aspirate(20, tubes["A1"])
    p20.dispense(20, plate["A9"])
    p20.drop_tip()
    p20.pick_up_tip()
    p20.aspirate(5, tubes["B5"])
    p20.dispense(5, plate["A9"])
    p20.mix(20, 5, plate["A9"])
    p20.drop_tip()
