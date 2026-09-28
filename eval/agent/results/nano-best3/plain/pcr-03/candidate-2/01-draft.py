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

    # Define each sample as its own liquid
    for well in source_plate.wells():
        well_name = well.name  # e.g., "A1"
        liq_name = f"sample_{well_name}"
        protocol.define_liquid(
            name=liq_name,
            description=f"Sample from {well_name}",
            display_color="#000000"
        )
        source_plate[well_name].load_liquid(liquid=liq_name, volume=10)

    # Load the p20 pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Transfer master mix and template to each well of the PCR plate
    for dest_well in dest_plate.wells():
        p20.pick_up_tip()
        p20.aspirate(18, reservoir["A1"])
        p20.dispense(18, dest_well)
        p20.aspirate(2, source_plate[dest_well.name])
        p20.dispense(2, dest_well)
        p20.drop_tip()
