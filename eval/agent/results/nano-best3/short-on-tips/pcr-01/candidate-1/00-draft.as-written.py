from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_8samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    # Define sample liquids
    for i in range(1,9):
        protocol.define_liquid(
            name=f"sample {i}", description=f"Sample {i}", display_color="#000000"
        )

    # Load liquids into tube rack wells
    tube_rack["A1"].load_liquid(liquid="master mix", volume=200)
    tube_rack["A2"].load_liquid(liquid="sample 1", volume=10)
    tube_rack["A3"].load_liquid(liquid="sample 2", volume=10)
    tube_rack["A4"].load_liquid(liquid="sample 3", volume=10)
    tube_rack["A5"].load_liquid(liquid="sample 4", volume=10)
    tube_rack["A6"].load_liquid(liquid="sample 5", volume=10)
    tube_rack["B1"].load_liquid(liquid="sample 6", volume=10)
    tube_rack["B2"].load_liquid(liquid="sample 7", volume=10)
    tube_rack["B3"].load_liquid(liquid="sample 8", volume=10)

    # Define target wells (column 1)
    target_wells = [
        plate["A1"], plate["B1"], plate["C1"], plate["D1"],
        plate["E1"], plate["F1"], plate["G1"], plate["H1"]
    ]

    # Transfer master mix and sample into each target well
    p300.pick_up_tip()
    for i in range(8):
        # Aspirate 20 ul master mix
        p300.aspirate(20, tube_rack["A1"])
        # Dispense master mix into target well
        p300.dispense(20, target_wells[i])
        # Aspirate 5 ul sample
        sample_well_name = ["A2","A3","A4","A5","A6","B1","B2","B3"][i]
        p300.aspirate(5, tube_rack[sample_well_name])
        # Dispense sample into target well
        p300.dispense(5, target_wells[i])
    p300.drop_tip()
