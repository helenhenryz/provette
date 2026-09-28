from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_master_mix_and_template", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20ul])
    
    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="master mix", display_color="#0000FF")
    template = protocol.define_liquid(name="template", description="template", display_color="#FF0000")
    
    # Load master mix into reservoir well A1
    reservoir["A1"].load_liquid(liquid=master_mix, volume=10000)
    
    # Load template into each well of the source plate (increase volume to ensure enough height)
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well = row + str(col)
            source_plate[well].load_liquid(liquid=template, volume=35)
    
    # Transfer 18 ul master mix and 2 ul template to each well of the PCR plate
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well = row + str(col)
            p20.pick_up_tip()
            p20.aspirate(18, reservoir["A1"])
            p20.dispense(18, dest_plate[well])
            p20.aspirate(2, source_plate[well])
            p20.dispense(2, dest_plate[well])
            p20.drop_tip()
