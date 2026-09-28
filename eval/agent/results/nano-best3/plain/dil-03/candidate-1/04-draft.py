from opentrons import protocol_api

metadata = {"protocolName": "BSA Standard Curve", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    
    # Define liquids
    bsa = protocol.define_liquid(name="bsa", description="BSA stock", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Water", display_color="#0000FF")
    
    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=bsa, volume=1000)
    reservoir["A1"].load_liquid(liquid=water, volume=2000)
    
    # Destination wells
    dest_wells = ["A1", "A2", "A2", "A3", "A4", "A5", "A6", "A7"]  # Using A2-A8 for standards, A1 for blank water
    
    # Dilution series parameters from plate map
    diluent_volumes = [0.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    transfer_volumes = [100.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]
    sources = ["stock", "well 1", "well 2", "well 3", "well 4", "well 5", "well 6", "well 7"]
    
    # Process each well
    for i in range(len(dest_wells)):
        dest = plate[dest_wells[i]]
        
        # Add diluent (water) if needed
        if diluent_volumes[i] > 0:
            p300.pick_up_tip()
            p300.aspirate(diluent_volumes[i], reservoir["A1"])
            p300.dispense(diluent_volumes[i], dest)
            p300.drop_tip()
        
        # Determine source well
        if sources[i] == "stock":
            source_well = tubes["A1"]
        else:
            source_num = int(sources[i].split()[1])
            source_well = plate["A" + str(source_num)]
        
        # Transfer stock (or mixture) into destination well
        p300.pick_up_tip()
        p300.aspirate(transfer_volumes[i], source_well)
        p300.dispense(transfer_volumes[i], dest)
        p300.drop_tip()
        
        # Mix: use 80% of well volume (80 ul) for 5 cycles
        mix_volume = 80.0
        for _ in range(5):
            p300.pick_up_tip()
            p300.aspirate(mix_volume, dest)
            p300.dispense(mix_volume, dest)
            p300.drop_tip()
        
        # Remove excess from last well (well 8)
        if i == 7:
            p300.pick_up_tip()
            p300.aspirate(50.0, dest)
            p300.drop_tip()
