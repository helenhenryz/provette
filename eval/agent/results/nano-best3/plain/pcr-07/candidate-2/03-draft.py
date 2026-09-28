from opentrons import protocol_api

metadata = {
    "protocolName": "pcr_setup_12_samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    # Temperature module and aluminium block
    temp_module = protocol.load_module("temperature module gen2", 2)
    aluminum_block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    # Reservoir for master mix
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    # Load pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    
    # Define liquids
    buffer_liquid = protocol.define_liquid(
        name="buffer",
        description="buffer mix",
        display_color="#0000FF"
    )
    polymerase_liquid = protocol.define_liquid(
        name="polymerase",
        description="DNA polymerase",
        display_color="#00FF00"
    )
    fwd_primer_liquid = protocol.define_liquid(
        name="fwd primer",
        description="forward primer",
        display_color="#FF0000"
    )
    rev_primer_liquid = protocol.define_liquid(
        name="rev primer",
        description="reverse primer",
        display_color="#FFFF00"
    )
    water_liquid = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#00FFFF"
    )
    # Define samples 1-12
    sample_liquids = {}
    for i in range(1, 13):
        sample_liquids[i] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color="#808080"
        )
    
    # Load liquids into aluminum block wells
    aluminum_block["A1"].load_liquid(liquid=buffer_liquid, volume=150)
    aluminum_block["A2"].load_liquid(liquid=polymerase_liquid, volume=10)
    aluminum_block["A3"].load_liquid(liquid=fwd_primer_liquid, volume=20)
    aluminum_block["A4"].load_liquid(liquid=rev_primer_liquid, volume=20)
    aluminum_block["A5"].load_liquid(liquid=water_liquid, volume=150)
    for i in range(1, 13):
        if i <= 6:
            well_name = f"C{i}"
        else:
            well_name = f"D{i-6}"
        liq = sample_liquids[i]
        aluminum_block[well_name].load_liquid(liquid=liq, volume=10)
    
    # Set temperature for cold block
    temp_module.set_temperature(4)
    
    # Build master mix in reservoir
    # Buffer
    p300.pick_up_tip()
    p300.aspirate(120, aluminum_block["A1"])
    p300.dispense(120, reservoir["A1"])
    p300.drop_tip()
    # Water (diluent) before polymerase
    p300.pick_up_tip()
    p300.aspirate(126, aluminum_block["A5"])
    p300.dispense(126, reservoir["A1"])
    p300.drop_tip()
    # Polymerase
    p20.pick_up_tip()
    p20.aspirate(6, aluminum_block["A2"])
    p20.dispense(6, reservoir["A1"])
    p20.drop_tip()
    # Fwd primer
    p20.pick_up_tip()
    p20.aspirate(12, aluminum_block["A3"])
    p20.dispense(12, reservoir["A1"])
    p20.drop_tip()
    # Rev primer
    p20.pick_up_tip()
    p20.aspirate(12, aluminum_block["A4"])
    p20.dispense(12, reservoir["A1"])
    p20.drop_tip()
    # Mix the master mix
    p300.pick_up_tip()
    for _ in range(3):
        p300.aspirate(200, reservoir["A1"])
        p300.dispense(200, reservoir["A1"])
    p300.drop_tip()
    # Aspirate total master mix into tip
    total_master_mix_vol = 276  # 120 + 126 + 6 + 12 + 12
    p300.pick_up_tip()
    p300.aspirate(total_master_mix_vol, reservoir["A1"])
    # Dispense master mix into each reaction well (23 ul each)
    for i in range(1, 13):
        p300.dispense(23, plate[f"A{i}"])
    p300.drop_tip()
    
    # Add 2 ul of each sample to its corresponding well
    for i in range(1, 13):
        p20.pick_up_tip()
        if i <= 6:
            sample_well = aluminum_block[f"C{i}"]
        else:
            sample_well = aluminum_block[f"D{i-6}"]
        p20.aspirate(2, sample_well)
        p20.dispense(2, plate[f"A{i}"])
        p20.drop_tip()
    
    # Deactivate temperature module
    temp_module.deactivate()
