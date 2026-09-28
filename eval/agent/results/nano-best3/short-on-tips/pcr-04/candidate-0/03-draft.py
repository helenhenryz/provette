from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR plate setup for 6 samples triplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    temp_mod = protocol.load_module("temperature module gen2", 4)
    strip = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="SYBR master mix with primers", display_color="#FF0000"
    )
    sample_1 = protocol.define_liquid(
        name="sample 1", description="cDNA sample 1", display_color="#00FF00"
    )
    sample_2 = protocol.define_liquid(
        name="sample 2", description="cDNA sample 2", display_color="#0000FF"
    )
    sample_3 = protocol.define_liquid(
        name="sample 3", description="cDNA sample 3", display_color="#FF00FF"
    )
    sample_4 = protocol.define_liquid(
        name="sample 4", description="cDNA sample 4", display_color="#00FFFF"
    )
    sample_5 = protocol.define_liquid(
        name="sample 5", description="cDNA sample 5", display_color="#FFFF00"
    )
    sample_6 = protocol.define_liquid(
        name="sample 6", description="cDNA sample 6", display_color="#800080"
    )

    # Load liquids into source wells
    tube_rack["A1"].load_liquid(liquid=master_mix, volume=200)
    strip["A1"].load_liquid(liquid=sample_1, volume=10)
    strip["A2"].load_liquid(liquid=sample_2, volume=10)
    strip["A3"].load_liquid(liquid=sample_3, volume=10)
    strip["A4"].load_liquid(liquid=sample_4, volume=10)
    strip["A5"].load_liquid(liquid=sample_5, volume=10)
    strip["A6"].load_liquid(liquid=sample_6, volume=10)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack])

    # Set temperature for the strip (4°C)
    temp_mod.set_temperature(4)

    # Destination wells list
    dest_wells = [
        "A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12",
        "B1","B2","B3","B4","B5","B6"
    ]

    # First, transfer master mix (8 ul) to all destination wells
    p20.pick_up_tip()
    for i, well in enumerate(dest_wells):
        p20.aspirate(8, tube_rack["A1"])
        p20.dispense(8, plate[well])
    # Drop tip after master mix transfers
    p20.drop_tip()

    # Then, for each sample, transfer 2 ul of sample to its 3 replicate wells
    for sample_idx in range(6):
        # Ensure any previous tip is dropped
        p20.drop_tip()
        # Pick up a fresh tip for this sample
        p20.pick_up_tip()
        # Get the 3 destination wells for this sample (consecutive)
        replicate_wells = dest_wells[sample_idx*3 : sample_idx*3 + 3]
        # Source well for this sample
        sample_source = strip["A" + str(sample_idx + 1)]
        # Transfer 2 ul to each of the 3 replicate wells
        for rep_well in replicate_wells:
            p20.aspirate(2, sample_source)
            p20.dispense(2, plate[rep_well])
        # Drop tip after finishing this sample
        p20.drop_tip()

    # Deactivate temperature module
    temp_mod.deactivate()
