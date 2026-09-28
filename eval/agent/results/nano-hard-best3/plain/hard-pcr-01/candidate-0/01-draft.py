from opentrons import protocol_api

metadata = {"protocolName": "PCR Setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "1")
    source_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    mix_reservoir = protocol.load_labware("nest_12_reservoir_15ml", "4")
    
    # Define master mix
    mix = protocol.define_liquid(
        name="mix", description="master mix", display_color="#0000FF"
    )
    mix_reservoir.wells_by_name()["A1"].load_liquid(liquid=mix, volume=1600)
    
    # Define source liquids (one per well) and load them
    for src_well in source_plate.wells():
        liq_name = f"sample_{src_well.name}"
        sample_liquid = protocol.define_liquid(
            name=liq_name, description=f"Sample from {src_well.name}", display_color="#FF0000"
        )
        src_well.load_liquid(liquid=sample_liquid, volume=5)
    
    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Transfer 15 ul mix + 5 ul template into each well
    for dest_well in plate.wells():
        p20.pick_up_tip()
        # aspirate 15 ul from master mix
        mix_well = mix_reservoir.wells_by_name()["A1"]
        p20.aspirate(15, mix_well)
        # dispense 15 ul mix into destination well
        p20.dispense(15, dest_well)
        # aspirate 5 ul from matching source well
        src_well = source_plate[dest_well.name]
        p20.aspirate(5, src_well)
        # dispense 5 ul template into destination well
        p20.dispense(5, dest_well)
        # drop tip
        p20.drop_tip()
