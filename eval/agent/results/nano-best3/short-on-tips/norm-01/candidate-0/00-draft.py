from opentrons import protocol_api

metadata = {"protocolName": "Normalization_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="water", display_color="#0000FF")
    sample_liquids = {}
    for i in range(1, 25):
        sample_liquids[i] = protocol.define_liquid(name=f"sample {i}", description=f"sample {i}", display_color="#000000")
    
    # Load liquids into source plate and reservoir
    # Well names for the 24 samples (row-major order)
    well_names = [f"{chr(65 + i // 12)}{(i % 12) + 1}" for i in range(24)]
    
    # Load sample liquids into source plate wells
    for i in range(24):
        well = source_plate[well_names[i]]
        well.load_liquid(liquid=sample_liquids[i+1], volume=sample_volumes[i])
    
    # Load water into reservoir well A1
    reservoir_well = reservoir["A1"]
    reservoir_well.load_liquid(liquid=water, volume=sum(diluent_volumes))
    
    # Perform transfers
    for i in range(24):
        p300.pick_up_tip()
        # Aspirate sample
        p300.aspirate(sample_volumes[i], source_plate[well_names[i]])
        # Dispense sample into destination well
        p300.dispense(sample_volumes[i], dest_plate[well_names[i]])
        # Aspirate water
        p300.aspirate(diluent_volumes[i], reservoir["A1"])
        # Dispense water into same destination well
        p300.dispense(diluent_volumes[i], dest_plate[well_names[i]])
        p300.drop_tip()
