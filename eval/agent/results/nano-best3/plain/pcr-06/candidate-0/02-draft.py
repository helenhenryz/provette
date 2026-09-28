from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware('opentrons_96_tiprack_20ul', 1)
    source_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    dest_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 3)
    reservoir = protocol.load_labware('nest_12_reservoir_15ml', 4)
    
    # Define liquids
    pcr_mix = protocol.define_liquid(name='pcr mix', description='PCR master mix', display_color='#FF0000')
    colony_1 = protocol.define_liquid(name='colony 1', description='Colony 1 resuspension', display_color='#00FF00')
    colony_2 = protocol.define_liquid(name='colony 2', description='Colony 2 resuspension', display_color='#00AA00')
    colony_3 = protocol.define_liquid(name='colony 3', description='Colony 3 resuspension', display_color='#008800')
    colony_4 = protocol.define_liquid(name='colony 4', description='Colony 4 resuspension', display_color='#006600')
    colony_5 = protocol.define_liquid(name='colony 5', description='Colony 5 resuspension', display_color='#004400')
    colony_6 = protocol.define_liquid(name='colony 6', description='Colony 6 resuspension', display_color='#002200')
    colony_6 = protocol.define_liquid(name='colony 6', description='Colony 6 resuspension', display_color='#002200')
    colony_7 = protocol.define_liquid(name='colony 7', description='Colony 7 resuspension', display_color='#001100')
    colony_8 = protocol.define_liquid(name='colony 8', description='Colony 8 resuspension', display_color='#0000FF')
    colony_9 = protocol.define_liquid(name='colony 9', description='Colony 9 resuspension', display_color='#1100FF')
    colony_10 = protocol.define_liquid(name='colony 10', description='Colony 10 resuspension', display_color='#2200FF')
    colony_11 = protocol.define_liquid(name='colony 11', description='Colony 11 resuspension', display_color='#3300FF')
    colony_12 = protocol.define_liquid(name='colony 12', description='Colony 12 resuspension', display_color='#4400FF')
    colony_13 = protocol.define_liquid(name='colony 13', description='Colony 13 resuspension', display_color='#5500FF')
    colony_14 = protocol.define_liquid(name='colony 14', description='Colony 14 resuspension', display_color='#6600FF')
    colony_15 = protocol.define_liquid(name='colony 15', description='Colony 15 resuspension', display_color='#7700FF')
    colony_16 = protocol.define_liquid(name='colony 16', description='Colony 16 resuspension', display_color='#8800FF')
    
    # Load liquids
    reservoir["A1"].load_liquid(liquid=pcr_mix, volume=1000)
    # Load colony liquids into source plate according to expected order
    source_plate["H1"].load_liquid(liquid=colony_1, volume=100)
    source_plate["G1"].load_liquid(liquid=colony_2, volume=100)
    source_plate["F1"].load_liquid(liquid=colony_3, volume=100)
    source_plate["E1"].load_liquid(liquid=colony_4, volume=100)
    source_plate["D1"].load_liquid(liquid=colony_5, volume=100)
    source_plate["C1"].load_liquid(liquid=colony_6, volume=100)
    source_plate["B1"].load_liquid(liquid=colony_7, volume=100)
    source_plate["A1"].load_liquid(liquid=colony_8, volume=100)
    source_plate["H2"].load_liquid(liquid=colony_9, volume=100)
    source_plate["G2"].load_liquid(liquid=colony_10, volume=100)
    source_plate["F2"].load_liquid(liquid=colony_11, volume=100)
    source_plate["E2"].load_liquid(liquid=colony_12, volume=100)
    source_plate["D2"].load_liquid(liquid=colony_13, volume=100)
    source_plate["C2"].load_liquid(liquid=colony_14, volume=100)
    source_plate["B2"].load_liquid(liquid=colony_15, volume=100)
    source_plate["A2"].load_liquid(liquid=colony_16, volume=100)
    
    # Load pipette
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tips])
    
    # Define the order of destination wells as expected by the plate map
    dest_well_names = ["H1", "G1", "F1", "E1", "D1", "C1", "B1", "A1", "H2", "G2", "F2", "E2", "D2", "C2", "B2", "A2"]
    
    # Distribute PCR mix and add colony samples
    for i, dest_well_name in enumerate(dest_well_names):
        # First tip: aspirate pcr mix and dispense
        p20.pick_up_tip()
        p20.aspirate(20, reservoir["A1"])
        dest_well = dest_plate[dest_well_name]
        p20.dispense(20, dest_well)
        p20.drop_tip()
        
        # Second tip: aspirate colony sample and dispense
        p20.pick_up_tip()
        source_well = source_plate[dest_well_name]
        p20.aspirate(1, source_well)
        p20.dispense(1, dest_well)
        # Mix the well
        p20.mix(5, 17, dest_well)
        p20.drop_tip()
        
    # Add a no-template control well (e.g., A3) with 20 ul pcr mix only
    no_template_well = dest_plate["A3"]
    p20.pick_up_tip()
    p20.aspirate(20, reservoir["A1"])
    p20.dispense(20, no_template_well)
    p20.drop_tip()
