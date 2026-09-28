from opentrons import protocol_api

metadata = {
    "protocolName": "PCR_setup_8_reactions",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", "2")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "3")
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "4")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")
    
    # Define liquids
    protocol.define_liquid(name="mix", description="2x master mix", display_color="#FF0000")
    protocol.define_liquid(name="water", description="nuclease-free water", display_color="#0000FF")
    for i in range(1, 9):
        protocol.define_liquid(name=f"template {i}", description=f"Template {i}", display_color="#000000")
    
    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid="mix", volume=500)
    reservoir["A1"].load_liquid(liquid="water", volume=500)
    tubes["A2"].load_liquid(liquid="template 1", volume=20)
    tubes["A3"].load_liquid(liquid="template 2", volume=20)
    tubes["A4"].load_liquid(liquid="template 3", volume=20)
    tubes["A5"].load_liquid(liquid="template 4", volume=20)
    tubes["A6"].load_liquid(liquid="template 5", volume=20)
    tubes["B1"].load_liquid(liquid="template 6", volume=20)
    tubes["B2"].load_liquid(liquid="template 7", volume=20)
    tubes["B3"].load_liquid(liquid="template 8", volume=20)
    
    # Load instruments
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    
    # Mapping from destination well to template source well
    template_mapping = {
        "A1": "A2",
        "A2": "A3",
        "A3": "A4",
        "A4": "A5",
        "A5": "A6",
        "A6": "B1",
        "A7": "B2",
        "A8": "B3"
    }
    
    # Transfer mix (50 ul) to each of the 8 reaction wells
    for i in range(8):
        dest_well = f"A{i+1}"
        # Transfer mix
        p300.pick_up_tip()
        p300.aspirate(50, tubes["A1"])
        p300.dispense(50, plate[dest_well])
        p300.drop_tip()
        # Transfer water
        p300.pick_up_tip()
        p300.aspirate(42, reservoir["A1"])
        p300.dispense(42, plate[dest_well])
        p300.drop_tip()
        # Transfer template
        src_well = template_mapping[dest_well]
        p20.pick_up_tip()
        p20.aspirate(8, tubes[src_well])
        p20.dispense(8, plate[dest_well])
        p20.drop_tip()
