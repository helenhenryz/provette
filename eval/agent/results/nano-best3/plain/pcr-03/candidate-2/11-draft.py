from opentrons import protocol_api

metadata = {"protocolName": "PCR master mix and template plating", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Define master mix
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    reservoir["A1"].load_liquid(liquid=master_mix, volume=10000)

    # Define each sample as its own liquid and load 40 ul into each source well
    for well in source_plate.wells():
        well_name = str(well).split(" of ")[0]  # Extract "A1", "B3", etc.
        sample_liquid_name = f"sample_{well_name}"
        # Define the liquid and capture the returned object
        sample_liquid = protocol.define_liquid(
            name=sample_liquid_name,
            description=f"Sample from {well_name}",
            display_color="#000000"
        )
        # Load 40 ul of this sample into the well (increased volume)
        source_plate[well_name].load_liquid(liquid=sample_liquid, volume=40)

    # Load the p20 pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Transfer master mix and template to each well of the PCR plate
    for dest_well in dest_plate.wells():
        # First, aspirate and dispense master mix with a single tip
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"])
        p20.dispense(18, dest_well)
        p20.drop_tip()
        
        # Then, aspirate template with a fresh tip and dispense
        p20.pick_up_tip()
        p20.aspirate(2, source_plate[str(dest_well).split(" of ")[0]])
        p20.dispense(2, dest_well)
        p20.drop_tip()
