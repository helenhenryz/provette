from opentrons import protocol_api

metadata = {
    "protocolName": "PCR setup with master mix and template addition",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    source_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)

    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    protocol.define_liquid(name="mix", description="master mix for qPCR", display_color="#0000FF")

    # Define source liquids for each well
    for row in "ABCDEFGHI":
        for col in range(1,13):
            well_name = f"{row}{col}"
            source_liquid_name = f"source_{well_name}"
            protocol.define_liquid(name=source_liquid_name,
                                   description=f"Sample from {well_name}",
                                   display_color="#FF0000")
    # Load master mix into reservoir
    reservoir["A1"].load_liquid(liquid="mix", volume=1600)

    # Load source liquids into source plate wells
    for row in "ABCDEFGHI":
        for col in range(1,13):
            well_name = f"{row}{col}"
            source_liquid_name = f"source_{well_name}"
            source_well = source_plate[well_name]
            source_well.load_liquid(liquid=source_liquid_name, volume=100)

    # Transfer mix and template into each well of destination plate
    for row in "ABCDEFGHI":
        for col in range(1,13):
            well_name = f"{row}{col}"
            dest_well = dest_plate[well_name]
            source_well = source_plate[well_name]

            # Pick up a new tip
            p300.pick_up_tip()

            # Aspirate 15 ul of master mix
            p300.aspirate(15, reservoir["A1"])

            # Dispense 15 ul into destination well
            p300.dispense(15, dest_well)

            # Aspirate 5 ul of template from source well
            p300.aspirate(5, source_well)

            # Dispense 5 ul into destination well
            p300.dispense(5, dest_well)

            # Drop tip
            p300.drop_tip()
