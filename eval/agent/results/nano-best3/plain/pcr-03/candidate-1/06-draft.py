from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_master_mix_and_template", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Load tip racks (two racks to have enough tips)
    tips_20ul_1 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_20ul_2 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    
    # Load pipette with both tip racks
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20ul_1, tips_20ul_2])
    
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="master mix", display_color="#0000FF")
    template = protocol.define_liquid(name="template", description="template", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="water", display_color="#00FFFF")
    
    # Load master mix into reservoir well A1
    reservoir["A1"].load_liquid(liquid=master_mix, volume=10000)
    
    # Load water into source plate well A1 (no-template control)
    source_plate["A1"].load_liquid(liquid=water, volume=35)
    
    # Load template into each well of the source plate (except A1) to ensure enough height
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well = row + str(col)
            if well != "A1":
                source_plate[well].load_liquid(liquid=template, volume=35)
    
    # Transfer 18 ul master mix and 2 ul template (or water) to each well of the PCR plate
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well = row + str(col)
            # Pick up tip
            p20.pick_up_tip()
            # Aspirate 18 ul master mix from reservoir A1
            p20.aspirate(18, reservoir["A1"])
            # Dispense 18 ul master mix into destination well
            p20.dispense(18, dest_plate[well])
            # Drop tip
            p20.drop_tip()
            
            # Pick up fresh tip
            p20.pick_up_tip()
            # Aspirate 2 ul from source plate well (water for A1, template for others)
            if well == "A1":
                p20.aspirate(2, source_plate[well])  # water
            else:
                p20.aspirate(2, source_plate[well])  # template
            # Dispense 2 ul into destination well
            p20.dispense(2, dest_plate[well])
            # Mix the well after adding template (or water) (mix 5 cycles of 16 ul)
            p20.mix(5, 16, dest_plate[well])
            # Drop tip
            p20.drop_tip()
