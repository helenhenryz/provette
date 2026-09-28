from opentrons import protocol_api

metadata = {"protocolName": "1:2 Drug Dilution into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    pbs = protocol.define_liquid(name="pbs", description="PBS buffer", display_color="#00FF00")
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=drug, volume=1500)
    reservoir["A1"].load_liquid(liquid=pbs, volume=1500)
    
    # Initialize source wells
    source = tuberack["A1"]  # drug source
    pbs_source = reservoir["A1"]  # PBS source
    
    # Perform serial dilution across wells A1-A12
    for i in range(12):
        well = plate["A" + str(i+1)]
        
        # Pick up a fresh tip for each well to avoid cross-contamination
        p300.pick_up_tip()
        
        # Add 100 ul of PBS (diluent) to the well
        p300.aspirate(100, pbs_source)
        p300.dispense(100, well)
        
        # Transfer 100 ul from source into the well
        p300.aspirate(100, source)
        p300.dispense(100, well)
        
        # Mix the well (use 160 ul, which is >20 ul minimum for p300)
        p300.mix(160, 5)
        
        # Update source for next iteration (except after the last well)
        if i < 11:
            source = well
        
        # Drop tip after processing the well
        p300.drop_tip()
    
    # Remove 100 ul from the last well to waste
    waste_well = tuberack["B1"]
    p300.pick_up_tip()
    p300.aspirate(100, well)  # well is the last processed well (A12)
    p300.dispense(100, waste_well)
    p300.drop_tip()
