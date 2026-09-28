from opentrons import protocol_api

metadata = {
    "protocolName": "MIC plate for 2 antibiotics",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])
    
    # Define liquids with display_color
    antibiotic_1 = protocol.define_liquid("antibiotic 1", "Antibiotic 1 stock solution", display_color="#FF0000")
    antibiotic_2 = protocol.define_liquid("antibiotic 2", "Antibiotic 2 stock solution", display_color="#00FF00")
    broth = protocol.define_liquid("broth", "Mueller-Hinton broth", display_color="#0000FF")
    culture = protocol.define_liquid("culture", "Bacterial culture", display_color="#FFFF00")
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=antibiotic_1, volume=2000)
    tuberack["A2"].load_liquid(liquid=antibiotic_2, volume=2000)
    reservoir["A1"].load_liquid(liquid=broth, volume=2000)
    tuberack["A3"].load_liquid(liquid=culture, volume=2000)
    
    # Waste well for excess
    waste_well = tuberack["A6"]
    
    # Process a row of wells with a given antibiotic source
    def process_row(row_letter, antibiotic_source):
        for col in range(1, 11):  # columns 1 to 10
            target_well = plate["{}{}".format(row_letter, col)]
            # Add 50 ul broth (diluent)
            p300.pick_up_tip()
            p300.aspirate(50, reservoir["A1"])
            p300.dispense(50, target_well)
            p300.mix(50)
            p300.drop_tip()
            # Determine source for the antibiotic transfer
            if col == 1:
                source = antibiotic_source
            else:
                source = plate["{}{}".format(row_letter, col-1)]
            # Transfer 50 ul from source into the well
            p300.pick_up_tip()
            p300.aspirate(50, source)
            p300.dispense(50, target_well)
            p300.mix(50)
            p300.drop_tip()
            # Remove 50 ul from the last well (col 10) to waste
            if col == 10:
                p300.pick_up_tip()
                p300.aspirate(50, target_wel
