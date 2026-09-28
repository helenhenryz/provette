from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_18plus2", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    sample_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description=None, display_color="#1f77b4")
    reservoir["A1"].load_liquid(liquid=master_mix, volume=10000)

    # Define each sample liquid and load into sample plate wells
    for i, well in enumerate(sample_plate.wells()):
        liquid_name = f"sample_{i+1}"
        sample_liquid = protocol.define_liquid(name=liquid_name, description=None, display_color="#888888")
        well.load_liquid(liquid=sample_liquid, volume=10)  # 10 ul starting volume

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Pick up tip
    p20.pick_up_tip()

    # Transfer for each well
    for dest_well, src_well in zip(pcr_plate.wells(), sample_plate.wells()):
        # Aspirate 18 ul master mix from reservoir
        p20.aspirate(18, reservoir["A1"])
        # Dispense 18 ul master mix into PCR plate well
        p20.dispense(18, dest_well)
        # Aspirate 2 ul template from sample plate well
        p20.aspirate(2, src_well)
        # Dispense 2 ul into PCR plate well
        p20.dispense(2, dest_well)

    # Drop tip
    p20.drop_tip()
