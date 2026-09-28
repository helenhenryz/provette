from opentrons import protocol_api

metadata = {
    "protocolName": "Dilute 24 serum samples 1 in 10 and transfer in duplicate",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    liquids = {}
    for i in range(1, 25):
        liquids[f"serum {i}"] = protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum sample {i}",
            display_color="#FF0000"
        )
    liquids["pbs"] = protocol.define_liquid(
        name="pbs",
        description="PBS buffer",
        display_color="#00FF00"
    )
    
    # Load labware
    tip_racks_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tip_racks_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    dilution_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 5)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 6)
    
    # Load liquids into source wells
    # Helper function to get well name for 96-well plate
    def well_name_96(idx):
        row_index = (idx-1) // 12
        col_index = (idx-1) % 12 + 1
        letters = "ABCDEFGHIJ"[:8]
        return f"{letters[row_index]}{col_index}"
    
    # Load serum liquids into tube rack wells according to expected pattern
    for i in range(1, 25):
        col_index = (i-1) // 6  # 0-3
        row = (i-1) % 6 + 1       # 1-6
        letters = "ABCD"
        well_name = f"{letters[col_index]}{row}"
        tuberack[well_name].load_liquid(liquid=liquids[f"serum {i}"], volume=50)
    # Load PBS into reservoir well A1
    reservoir["A1"].load_liquid(liquid=liquids["pbs"], volume=10800)
    
    # Load instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks_300])
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tip_racks_1000])
    
    # Loop over samples
    for i in range(1, 25):
        # Compute well name for serum i
        col_index = (i-1) // 6  # 0-3
        row = (i-1) % 6 + 1       # 1-6
        letters = "ABCD"
        src_well_name = f"{letters[col_index]}{row}"
        src_dilution_well = dilution_plate[src_well_name]
        dest_idx1 = 2*i - 1
        dest_idx2 = 2*i
        dest_well_1 = well_name_96(dest_idx1)
        dest_well_2 = well_name_96(dest_idx2)
        
        # Pick up tips
        p300.pick_up_tip()
        # Aspirate 50 µl serum from tube rack
        p300.aspirate(50, tuberack[src_well_name])
        # Dispense 50 µl into dilution plate well
        p300.dispense(50, src_dilution_well)
        # Pick up tip for p1000
        p1000.pick_up_tip()
        # Aspirate 450 µl PBS from reservoir
        p1000.aspirate(450, reservoir["A1"])
        # Dispense 450 µl into dilution plate well
        p1000.dispense(450, src_dilution_well)
        # Mix the well to ensure homogeneity
        p1000.mix(src_dilution_well, 5)  # Fixed argument order
        # Aspirate 100 µl from dilution plate well
        p300.aspirate(100, src_dilution_well)
        # Dispense 100 µl into first destination well
        p300.dispense(100, elisa_plate[dest_well_1])
        # Aspirate another 100 µl from dilution plate well
        p300.aspirate(100, src_dilution_well)
        # Dispense 100 µl into second destination well
        p300.dispense(100, elisa_plate[dest_well_2])
        # Drop tip for p300
        p300.drop_tip()
        # Drop tip for p1000
        p1000.drop_tip()
