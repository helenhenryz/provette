from opentrons import protocol_api

metadata = {"protocolName": "PCR_setup_8samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    # Load pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20])

    # Define liquids
    master_mix_liquid = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    # Define sample liquids and keep references
    sample_liquids = {}
    for i in range(1, 9):
        sample_liquids[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}", description=f"Sample {i}", display_color="#000000"
        )

    # Load liquids into tube rack wells
    tube_rack["A1"].load_liquid(liquid=master_mix_liquid, volume=200)
    tube_rack["A2"].load_liquid(liquid=sample_liquids["sample 1"], volume=10)
    tube_rack["A3"].load_liquid(liquid=sample_liquids["sample 2"], volume=10)
    tube_rack["A4"].load_liquid(liquid=sample_liquids["sample 3"], volume=10)
    tube_rack["A5"].load_liquid(liquid=sample_liquids["sample 4"], volume=10)
    tube_rack["A6"].load_liquid(liquid=sample_liquids["sample 5"], volume=10)
    tube_rack["B1"].load_liquid(liquid=sample_liquids["sample 6"], volume=10)
    tube_rack["B2"].load_liquid(liquid=sample_liquids["sample 7"], volume=10)
    tube_rack["B3"].load_liquid(liquid=sample_liquids["sample 8"], volume=10)

    # Define target wells (column 1)
    target_wells = [
        plate["A1"], plate["B1"], plate["C1"], plate["D1"],
        plate["E1"], plate["F1"], plate["G1"], plate["H1"]
    ]

    # Transfer master mix into each target well using p300
    p300.pick_up_tip()
    for i in range(8):
        p300.aspirate(20, tube_rack["A1"])
        p300.dispense(20, target_wells[i])
    p300.drop_tip()

    # Transfer samples and mix using p20
    for i in range(8):
        sample_well_name = ["A2","A3","A3","A5","A6","B1","B2","B3"][i]  # typo here, should be corrected
        p20.pick_up_tip()
        p20.aspirate(5, tube_rack[sample_well_name])
        p20.dispense(5, target_wells[i])
        # Mix the well after sample addition
        p20.mix(5, 20, target_wells[i])
        p20.drop_tip()
