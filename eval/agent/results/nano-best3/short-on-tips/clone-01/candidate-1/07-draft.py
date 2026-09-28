from opentrons import protocol_api

metadata = {
    "protocolName": "restriction_digest_setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer_liquid = protocol.define_liquid(name="buffer", description="10x buffer", display_color="#0000FF")
    enzyme_liquid = protocol.define_liquid(name="enzyme", description="restriction enzyme", display_color="#00FF00")
    water_liquid = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#00FFFF")
    plasmid_liquids = {}
    for i in range(1, 13):
        plasmid_liquids[i] = protocol.define_liquid(name=f"plasmid {i}", description=f"plasmid {i}", display_color="#FF0000")
    
    # Load temperature module on slot 1
    temp_module = protocol.load_module("temperature module gen2", 1)
    # Set temperature to 4°C
    temp_module.set_temperature(4)
    # Load the aluminium block onto the temperature module
    block = temp_module.load_labware("opentrons_96_aluminumblock_generic_pcr_strip_200ul")
    # Load tip rack for p300_multi on slot 2
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    # Load tip rack for p20_single on slot 4
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    # Load plate on slot 3
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    # Load pipettes
    p300_multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tips])
    p20_single = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])
    
    # Load plasmid liquids into column A wells (A1-A12) with 10 µL each
    for i in range(1, 13):
        well_name = f"A{i}"
        block[well_name].load_liquid(liquid=plasmid_liquids[i], volume=10)
    
    # Load buffer into well B1 with 30 µL
    block["B1"].load_liquid(liquid=buffer_liquid, volume=30)
    # Load enzyme into well C1 with 30 µL
    block["C1"].load_liquid(liquid=enzyme_liquid, volume=30)
    # Load water into well D1 with 150 µL
    block["D1"].load_liquid(liquid=water_liquid, volume=150)
    
    # Transfer 2 µL buffer to each of 12 destination wells
    p300_multi.pick_up_tip()
    p300_multi.aspirate(30, block["B1"])  # aspirate 30 µL buffer
    for i in range(1, 13):
        p300_multi.dispense(2, plate[f"A{i}"])
    p300_multi.drop_tip()
    
    # Transfer 12 µL water to each of 12 destination wells
    p300_multi.pick_up_tip()
    p300_multi.aspirate(150, block["D1"])  # aspirate 150 µL water
    for i in range(1, 13):
        p300_multi.dispense(12, plate[f"A{i}"])
    p300_multi.drop_tip()
    
    # Transfer 1 µL enzyme to each of 12 destination wells
    p300_multi.pick_up_tip()
    p300_multi.aspirate(30, block["C1"])  # aspirate 30 µL enzyme
    for i in range(1, 13):
        p300_multi.dispense(1, plate[f"A{i}])
    p300_multi.drop_tip()
    
    # Transfer plasmids 1-8 (2x4 block)
    p300_multi.pick_up_tip()
    p300_multi.aspirate(20, block["A1"])  # aspirate from the 2x4 block (min 20 µL)
    p300_multi.dispense(5, plate["A1"])  # dispense into the 2x4 block of destination wells
    p300_multi.drop_tip()
    
    # Transfer plasmids 9-12 individually using p20_single
    for i in range(9, 13):
        p20_single.pick_up_tip()
        p20_single.aspirate(5, block[f"A{i}"])  # aspirate 5 µL from plasmid well
        p20_single.dispense(5, plate[f"A{i}"])  # dispense 5 µL into destination well
        p20_single.drop_tip()
        
    # Mix plasmids 9-12 in their wells
    for i in range(9, 13):
        p20_single.pick_up_tip()
        p20_single.mix(5, 15, plate[f"A{i}])
        p20_single.drop_tip()
