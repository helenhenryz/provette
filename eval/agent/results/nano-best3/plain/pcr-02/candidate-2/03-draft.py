from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_24samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#0000FF")
    samples = {}
    for i in range(1, 25):
        samples[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color="#000000")
    
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_racks])
    
    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=master_mix, volume=500)
    reservoir["A2"].load_liquid(liquid=water, volume=500)
    
    # Define 24 destination wells (A1-D6) on the plate
    plate_wells = [f"{col}{row}" for col in "ABCD" for row in range(1,7)]
    
    # Load samples into tube rack wells
    for i, well in enumerate(tube_rack.well_names()):
        tube_rack[well].load_liquid(liquid=samples[f"sample {i+1}"], volume=10)
    
    # Perform transfers for each of the 24 reactions
    for i in range(24):
        well = plate_wells[i]
        tube_well = tube_rack.well_names()[i]
        
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
        p20.aspirate(2, tube_rack[tube_well])
        p20.dispense(2, plate[well])
        p20.drop_tip()
        
        # Mix the well
        p20.mix(10, 5, plate[well])
