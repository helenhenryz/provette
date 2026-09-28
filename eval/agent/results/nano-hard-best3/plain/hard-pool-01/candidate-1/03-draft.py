from opentrons import protocol_api

metadata = {
    "protocolName": "Pool 25ul from each of 96 libraries",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 3)
    
    # Load each library into a well of the plate
    for i, well in enumerate(plate.wells()):
        lib = protocol.define_liquid(
            name=f"library {i+1}",
            description=f"Library {i+1}",
            display_color="#FF0000"
        )
        well.load_liquid(liquid=lib, volume=100)
    
    # Get the pool tube
    pool_tube = tubes["A1"]
    
    # Load the p300 pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Pool 25 ul from each well into the pool tube
    wells = list(plate.wells())
    for idx, well in enumerate(wells):
        p300.pick_up_tip()
        p300.aspirate(25, well)
        p300.dispense(25, pool_tube)
        if idx == len(wells) - 1:
            # Last well: mix instead of dropping tip immediately
            p300.mix(5, 1920, pool_tube)
            p300.drop_tip()
        else:
            p300.drop_tip()
