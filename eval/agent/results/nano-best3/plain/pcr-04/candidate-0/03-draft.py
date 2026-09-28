from opentrons import protocol_api

metadata = {"protocolName": "qPCR_plate_setup_6samples_triplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    master_mix_tubes = protocol.load_labware("opentrons_24_tuberack_nest_2ml_snapcap", 4)
    water_tube = master_mix_tubes["A2"]  # water source
    temp_mod = protocol.load_module("temperature module gen2", 3)
    strip_tubes = temp_mod.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # Set temperature to 4°C to preserve cDNA samples
    temp_mod.set_temperature(4)

    # Define liquids
    master_mix_liquid = protocol.define_liquid(
        name="master mix",
        description="SYBR master mix with primers",
        display_color="#FF0000"
    )
    water_liquid = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#000000"
    )
    sample1_liquid = protocol.define_liquid(
        name="sample 1",
        description="cDNA sample 1",
        display_color="#00FF00"
    )
    sample2_liquid = protocol.define_liquid(
        name="sample 2",
        description="cDNA sample 2",
        display_color="#0000FF"
    )
    sample3_liquid = protocol.define_liquid(
        name="sample 3",
        description="cDNA sample 3",
        display_color="#FFFF00"
    )
    sample4_liquid = protocol.define_liquid(
        name="sample 4",
        description="cDNA sample 4",
        display_color="#FF00FF"
    )
    sample5_liquid = protocol.define_liquid(
        name="sample 5",
        description="cDNA sample 5",
        display_color="#00FFFF"
    )
    sample6_liquid = protocol.define_liquid(
        name="sample 6",
        description="cDNA sample 6",
        display_color="#808080"
    )

    # Load liquids into source wells with realistic starting volumes
    master_mix_tubes["A1"].load_liquid(liquid=master_mix_liquid, volume=200)
    water_tube.load_liquid(liquid=water_liquid, volume=20)
    strip_tubes["A1"].load_liquid(liquid=sample1_liquid, volume=10)
    strip_tubes["A2"].load_liquid(liquid=sample2_liquid, volume=10)
    strip_tubes["A3"].load_liquid(liquid=sample3_liquid, volume=10)
    strip_tubes["A4"].load_liquid(liquid=sample4_liquid, volume=10)
    strip_tubes["A5"].load_liquid(liquid=sample5_liquid, volume=10)
    strip_tubes["A6"].load_liquid(liquid=sample6_liquid, volume=10)

    # Perform transfers for 18 reaction wells (6 samples × 3 replicates)
    for i, well in enumerate(plate.wells()[:18]):
        sample_idx = i // 3  # 0‑5, each sample used for 3 consecutive wells
        # --- Add master mix (8 µL) ---
        p20.pick_up_tip()
        p20.aspirate(8, master_mix_tubes["A1"])
        p20.dispense(8, well)
        p20.drop_tip()
        # --- Add sample (2 µL) ---
        sample_source = strip_tubes["A" + str(sample_idx + 1)]
        p20.pick_up_tip()
        p20.aspirate(2, sample_source)
        p20.dispense(2, well)
        # Mix the well (5 cycles, 8 µL total, ~80 % of well volume)
        p20.mix(5, 8, well)
        p20.drop_tip()
    
    # Add a no‑template control well (e.g., H12) with 8 µL master mix + 2 µL water
    p20.pick_up_tip()
    p20.aspirate(8, master_mix_tubes["A1"])
    p20.dispense(8, plate["H12"])
    p20.aspirate(2, water_tube)
    p20.dispense(2, plate["H12"])
    p20.mix(5, 8, plate["H12"])
    p20.drop_tip()
    
    # Deactivate temperature module after protocol completion
    temp_mod.deactivate()
