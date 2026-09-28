from opentrons import protocol_api

metadata = {
    "protocolName": "pcr_setup_12_samples",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    # Temperature module and tube rack
    temp_module = protocol.load_module("temperature module gen2", 2)
    cold_block = temp_module.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    # Reservoir for master mix
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
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
        liquid = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Sample {i}",
            display_color="#808080"
        )
        sample_liquids[i] = liquid
    
    # Load liquids into cold block wells
    cold_block["A1"].load_liquid(liquid=buffer_liquid, volume=150)
    cold_block["A2"].load_liquid(liquid=polymerase_liquid, volume=10)
    cold_block["A3"].load_liquid(liquid=fwd_primer_liquid, volume=20)
    cold_block["A4"].load_liquid(liquid=rev_primer_liquid, volume=20)
    cold_block["A5"].load_liquid(liquid=water_liquid, volume=150)
    for i in range(1, 13):
        if i <= 6:
            well_name = f"C{i}"
        else:
            well_name = f"D{i-6}"
        liq = sample_liquids[i]
        cold_block[well_name].load_liquid(liquid=liquid, volume=10)
    
    # Master mix volumes
    vol_buffer = 120
    vol_polymerase = 6
    vol_fwd_primer = 12
    vol_rev_primer = 12
    vol_water = 126
    total_master_mix_vol = vol_buffer + vol_polymerase + vol_fwd_primer + vol_rev_primer + vol_water  # 276
    
    # Build master mix in reservoir
    p300.pick_up_tip()
    # Buffer
    p300.aspirate(vol_buffer, cold_block["A1"])
    p300.dispense(vol_buffer, reservoir["A1"])
    # Polymerase
    p300.aspirate(vol_polymerase, cold_block["A2"])
    p300.dispense(vol_polymerase, reservoir["A1"])
    # Fwd primer
    p300.aspirate(vol_fwd_primer, cold_block["A3"])
    p300.dispense(vol_fwd_primer, reservoir["A1"])
    # Rev primer
    p300.aspirate(vol_rev_primer, cold_block["A4"])
    p300.dispense(vol_rev_primer, reservoir["A1"])
    # Water
    p300.aspirate(vol_water, cold_block["A5"])
    p300.dispense(vol_water, reservoir["A1"])
    # Mix the master mix
    for _ in range(3):
        p300.aspirate(10, reservoir["A1"])
        p300.dispense(10, reservoir["A1"])
    # Dispense master mix into each reaction well (23 ul each)
    for i in range(1, 13):
        p300.dispense(23, plate[f"A{i}"])
    p300.drop_tip()
    
    # Add 2 ul of each sample to its corresponding well
    for i in range(1, 13):
        p300.pick_up_tip()
        if i <= 6:
            sample_well = cold_block[f"C{i}"]
        else:
            sample_well = cold_block[f"D{i-6}"]
        p300.aspirate(2, sample_well)
        p300.dispense(2, plate[f"A{i}"])
        p300.drop_tip()
