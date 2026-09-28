from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup with Master Mix and Template",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    sample_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix", description="PCR master mix", display_color="#FF0000"
    )
    template = protocol.define_liquid(
        name="template", description="Template DNA", display_color="#00FF00"
    )

    # Load liquids onto deck
    reservoir["A1"].load_liquid(liquid=master_mix, volume=10000)
    for well in sample_plate.wells():
        well.load_liquid(liquid=template, volume=100)

    # Transfer 2 ul template + 18 ul master mix into each well of pcr_plate
    for row in "ABCDEFGH":
        for col in range(1, 13):
            name = row + str(col)
            p20.pick_up_tip()
            # aspirate 2 ul from sample plate well
            p20.aspirate(2, sample_plate[name])
            # dispense 2 ul into pcr plate well
            p20.dispense(2, pcr_plate[name])
            # aspirate 18 ul from reservoir
            p20.aspirate(18, reservoir["A1"])
            # dispense 18 ul into pcr plate well
            p20.dispense(18, pcr_plate[name])
            # drop tip
            p20.drop_tip()
