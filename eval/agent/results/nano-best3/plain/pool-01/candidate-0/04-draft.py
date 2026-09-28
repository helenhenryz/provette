from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 5ul from each of 48 libraries into a tube",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    target_tube = tube_rack["A1"]
    
    # Define liquids and load them into plate wells
    for i in range(48):
        lib_liquid = protocol.define_liquid(
            name=f"library {i+1}",
            description=f"Library {i+1}",
            display_color=f"#000000"
        )
        well = plate.wells()[i]
        well.load_liquid(liquid=lib_liquid, volume=200)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Pool 5 ul from each library into target tube
    for i in range(48):
        src_well = plate.wells()[i]
        p20.pick_up_tip()
        p20.aspirate(5, src_well)
        p20.dispense(5, target_tube)
        p20.drop_tip()
    
    # Mix the pooled tube
    p20.pick_up_tip()
    p20.mix(10, 10, target_tube)
    p20.drop_tip()
