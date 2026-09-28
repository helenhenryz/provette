from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup with master mix and template addition",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    source_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])

    # Define liquids
    mix = protocol.define_liquid(name="mix", description="master mix for qPCR", display_color="#0000FF")
    
    # Define source liquids for each well and store objects
    source_liquids = {}
    for row in "ABCDEFGH":
        for col in range(1,13):
            well_name = f"{row}{col}"
            if well_name == "H12":
                # NTC well: water instead of sample
                water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#00FFFF")
                source_liquids[well_name] = water
            else:
                source_liquid_obj = protocol.define_liquid(name=f"source_{well_name}",
                                                          description=f"Sample from {well_name}",
                                                          display_color="#FF0000")
                source_liquids[well_name] = source_liquid_obj

    # Load master mix into reservoir
    reservoir["A1"].load_liquid(liquid=mix, volume=1600)
    
    # Load source liquids into source plate wells
    for row in "ABCDEFGH":
        for col in range(1,13):
            well_name = f"{row}{col}"
            source_well = source_plate[well_name]
            source_well.load_liquid(liquid=source_liquids[well_name], volume=100)

    # Transfer mix and template into each well of destination plate
    for row in "ABCDEFGH":
        for col in range(1,13):
            well_name = f"{row}{col}"
            dest_well = dest_plate[well_name]
            source_well = source_plate[well_name]

            # Pick up a new tip
            p20.pick_up_tip()

            # Aspirate 5 ul of template (or water for NTC)
            p20.aspirate(5, source_well)

            # Dispense 5 ul into destination well
            p20.dispense(5, dest_well)

            # Aspirate 15 ul of master mix from reservoir (stay in liquid)
            p20.aspirate(15, reservoir["A1"].bottom(0.5))

            # Dispense 15 ul into destination well
            p20.dispense(15, dest_well)

            # Mix the well
            p20.mix(5, 5, dest_well)

            # Drop tip
            p20.drop_tip()
