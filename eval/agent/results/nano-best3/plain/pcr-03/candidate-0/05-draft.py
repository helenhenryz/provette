from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup with Master Mix and Template",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    sample_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    pcr_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    template = protocol.define_liquid(
        name="template", description="Template DNA", display_color="#00FF00"
    )
    water = protocol.define_liquid(
        name="water", description="Nuclease-free water", display_color="#0000FF"
    )

    # Load 18 ul master mix into every well of the PCR plate
    for row in "ABCDEFGH":
        for col in range(1, 13):
            name = row + str(col)
            pcr_plate[name].load_liquid(liquid=master_mix, volume=18)

    # Load template (100 ul) into all sample plate wells except H12
    all_names = [f"{row}{col}" for row in "ABCDEFGH" for col in range(1, 13)]
    for name in all_names:
        if name != "H12":
            sample_plate[name].load_liquid(liquid=template, volume=100)
    # Load water (100 ul) into well H12 for no‑template control
    sample_plate["H12"].load_liquid(liquid=water, volume=100)

    # For each well in the PCR plate, add 2 ul of template (or water) and mix
    for row in "ABCDEFGH":
        for col in range(1, 13):
            name = row + str(col)
            p20.pick_up_tip()
            # aspirate 2 ul from the sample plate well (template or water)
            p20.aspirate(2, sample_plate[name])
            # dispense into the PCR plate well
            p20.dispense(2, pcr_plate[name])
            # mix the well to combine the two liquids
            p20.mix(5, 16, pcr_plate[name])
            # drop tip
            p20.drop_tip()
