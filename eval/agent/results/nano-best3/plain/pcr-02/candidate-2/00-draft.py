from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#0000FF")
    for i in range(1, 25):
        protocol.define_liquid(name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color="#000000")
    
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid="master mix", volume=300)
    reservoir["A2"].load_liquid(liquid="water", volume=300)
    
    # Define well names for the tube rack (24 wells)
    well_names = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6","C1","C2","C3","C4","C5","C6","D1","D2","D3","D4","D5","D6"]
    
    # Load samples into tube rack wells
    for i, well in enumerate(well_names, start=1):
        tubes[well].load_liquid(liquid=f"sample {i}", volume=10)
    
    # Perform transfers for each of the 24 reactions
    for i, well in enumerate(well_names, start=1):
        # Add 12.5 ul master mix
        p20.pick_up_tip()
        p20.aspirate(12.5, reservoir["A1"])
        p20.dispense(12.5, plate[well])
        p20.drop_tip()
        
        # Add 10.5 ul water
        p20.pick_up_tip()
        p20.aspirate(10.5, reservoir["A2"])
        p20.dispense(10.5, plate[well])
        p20.drop_tip()
        
        # Add 2 ul sample
        p20.pick_up_tip()
        p20.aspirate(2, tubes[well])
        p20.dispense(2, plate[well])
        p20.drop_tip()
