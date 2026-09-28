from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="PCR master mix", display_color='#1f77b4')
    sample_liquids = {}
    for i in range(1, 9):
        sample_liquids[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color='#ff7f0e')

    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid=master_mix, volume=200)
    sample_wells = ["A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3"]
    for i, well in enumerate(sample_wells):
        tuberack[well].load_liquid(liquid=sample_liquids[f"sample {i+1}"], volume=10)

    # Set up reactions: 8 wells in column A1-A8
    for i in range(8):
        # Add 20 ul master mix
        p20.pick_up_tip()
        p20.aspirate(20, tuberack["A1"])
        p20.dispense(20, plate["A"+str(i+1)])
        p20.drop_tip()

        # Add 5 ul sample
        p20.pick_up_tip()
        p20.aspirate(5, tuberack[sample_wells[i]])
        p20.dispense(5, plate["A"+str(i+1)])
        p20.drop_tip()
