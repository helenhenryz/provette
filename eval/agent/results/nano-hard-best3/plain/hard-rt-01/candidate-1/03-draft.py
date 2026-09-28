from opentrons import protocol_api

metadata = {"protocolName": "RT_reverse_transcription", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x RT buffer", display_color="#0000FF")
    rt = protocol.define_liquid(name="rt", description="Reverse transcriptase", display_color="#00FF00")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFA500")
    primers = protocol.define_liquid(name="primers", description="Random primers", display_color="#800080")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#00FFFF")
    
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Load temperature module and block
    temp_module = protocol.load_module("temperature module gen2", 2)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    
    # Set temperature to 4°C for the block
    temp_module.set_temperature(4)
    
    # Load source plate with RNA samples
    rna_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Load destination plate (PCR plate)
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)
    
    # Load liquids into source wells
    block["A1"].load_liquid(liquid=buffer, volume=200)
    block["A2"].load_liquid(liquid=rt, volume=50)
    block["A3"].load_liquid(liquid=dntp, volume=100)
    block["A4"].load_liquid(liquid=primers, volume=100)
    block["A5"].load_liquid(liquid=water, volume=500)
    
    # Load RNA samples into plate wells (increase volume to avoid shallow liquid)
    for i in range(1, 13):
        rna_liquid = protocol.define_liquid(name=f"rna {i}", description=f"RNA sample {i}", display_color=f"#{i*100:03X}")
        rna_plate[f"A{i}"].load_liquid(liquid=rna_liquid, volume=60)  # increased volume
    
    # Define destination wells
    dest_wells = list(dest_plate.wells())[:24]
    
    # Process each component sequentially to avoid tip overflow and contamination
    # 1. Buffer (4 ul per well)
    total_buffer_vol = 4 * 24  # 96 ul total
    buffer_remaining = total_buffer_vol
    for i, well in enumerate(dest_wells):
        if buffer_remaining <= 0:
            break
        # Calculate how much to dispense in this step (max 20 ul per aspirate)
        dispense_vol = min(20, buffer_remaining)
        # Aspirate from buffer source
        p20.pick_up_tip()
        p20.aspirate(dispense_vol, block["A1"])
        # Dispense into the appropriate wells (4 ul each)
        # We'll dispense 4 ul per well, so we need to track which wells still need buffer
        # For simplicity, we'll dispense 4 ul into each well that still needs buffer
        # This is a simplified approach; in practice, we'd track per-well needs
        # Here we just dispense 4 ul into each well until buffer_remaining is exhausted
        if dispense_vol >= 4:
            p20.dispense(4, well)
            buffer_remaining -= 4
        p20.drop_tip()
    
    # 2. Water (5 ul for reactions, 6 ul for controls)
    total_water_vol = 0
    for i, well in enumerate(dest_wells):
        if i < 12:
            total_water_vol += 5  # reaction wells
        else:
            total_water_vol += 6  # control wells
    water_remaining = total_water_vol
    for i, well in enumerate(dest_wells):
        if water_remaining <= 0:
            break
        dispense_vol = min(20, water_remaining)
        p20.pick_up_tip()
        p20.aspirate(dispense_vol, block["A5"])
        # Dispense 5 ul for reactions, 6 ul for controls
        if i < 12:
            p20.dispense(5, well)
            water_remaining -= 5
        else:
            p20.dispense(6, well)
            water_remaining -= 6
        p20.drop_tip()
    
    # 3. dNTP (1 ul per well)
    dntp_remaining = 24  # 1 ul per well
    for i, well in enumerate(dest_wells):
        if dntp_remaining <= 0:
            break
        p20.pick_up_tip()
        p20.aspirate(1, block["A3"])
        p20.dispense(1, well)
        p20.drop_tip()
        dntp_remaining -= 1
    
    # 4. Primers (1 ul per well)
    primers_remaining = 24  # 1 ul per well
    for i, well in enumerate(dest_wells):
        if primers_remaining <= 0:
            break
        p20.pick_up_tip()
        p20.aspirate(1, block["A4"])
        p20.dispense(1, well)
        p20.drop_tip()
        primers_remaining -= 1
    
    # 5. RNA samples (8 ul per well)
    rna_remaining = 8 * 24  # 8 ul per well
    for i, well in enumerate(dest_wells):
        if rna_remaining <= 0:
            break
        p20.pick_up_tip()
        # Determine which RNA sample to use
        if i < 12:
            rna_index = i + 1
        else:
            rna_index = i - 12 + 1
        p20.aspirate(8, rna_plate[f"A{rna_index}"])
        p20.dispense(8, well)
        p20.drop_tip()
        rna_remaining -= 8
    
    # 6. Reverse transcriptase (1 ul for reactions only)
    rt_remaining = 12  # 1 ul per reaction well
    for i, well in enumerate(dest_wells):
        if i < 12:  # only reaction wells
            if rt_remaining <= 0:
                break
                # This condition should never trigger here
            p20.pick_up_tip()
            p20.aspirate(1, block["A2"])
            p20.dispense(1, well)
            p20.drop_tip()
            rt_remaining -= 1
    
    # Deactivate temperature module
    temp_module.deactivate()
