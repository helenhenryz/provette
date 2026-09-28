from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_96", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_master = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_samples = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # Define master mix
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)
    
    # Define water for NTC
    water = protocol.define_liquid(
        name="water", description="Nuclease-free water", display_color="#FFFFFF"
    )
    # Load water into well A1 of source plate (will be used as no‑template control)
    source_plate["A1"].load_liquid(liquid=water, volume=100)
    
    # Define sample liquids (one per well) and load them
    well_names = [row + str(col) for row in "ABCDEFGH" for col in range(1,13)]
    for well_name in well_names:
        # Skip the NTC well (A1) for sample loading
        if well_name == "A1":
            continue
        sample_liquid = protocol.define_liquid(
            name=f"sample_{well_name}", description=f"Sample from {well_name}", display_color="#000000"
        )
        source_plate[well_name].load_liquid(liquid=sample_liquid, volume=100)
    
    # Load p20 pipettes
    p20_master = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_master])
    p20_sample = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_samples])
    
    # Transfer 18 ul master mix to each PCR well using p20_master (reusing the same tip)
    for well_name in well_names:
        p20_master.pick_up_tip()
        p20_master.aspirate(18, reservoir["A1"])
        p20_master.dispense(18, pcr_plate[well_name])
        # Keep the tip, do not drop yet
    # After all dispenses, drop the tip
    p20_master.drop_tip()
    
    # Transfer 2 ul template (or water for NTC) to each PCR well using p20_sample (fresh tip each time)
    for well_name in well_names:
        if well_name == "A1":
            # NTC: aspirate 2 ul water
            p20_sample.pick_up_tip()
            p20_sample.aspirate(2, source_plate[well_name])
            p20_sample.dispense(2, pcr_plate[well_name])
            # Mix after dispensing (≈80% of well volume)
            p20_sample.mix(16, 1, pcr_plate[well_name])
            p20_sample.drop_tip()
        else:
            p20_sample.pick_up_tip()
            p20_sample.aspirate(2, source_plate[well_name])
            p20_sample.dispense(2, pcr_plate[well_name])
            # Mix after dispensing (≈80% of well volume)
            p20_sample.mix(16, 1, pcr_plate[well_name])
            p20_sample.drop_tip()
