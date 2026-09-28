from opentrons import protocol_api

metadata = {"protocolName": "SDS-PAGE Sample Prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 2)
    dye_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    dye = protocol.define_liquid(
        name="dye", description="4x loading dye", display_color="#FFA500"
    )
    # Define sample liquids and store them in a dict
    sample_liquids = {}
    for i in range(1, 13):
        sample_liquids[f"sample {i}"] = protocol.define_liquid(
            name=f"sample {i}",
            description=f"Protein sample {i}",
            display_color="#000000"
        )

    # Load liquids onto deck
    # Load each sample liquid into its corresponding well in source plate
    for i in range(1, 13):
        source_plate[f"A{i}"].load_liquid(liquid=sample_liquids[f"sample {i}"], volume=100)
    # Load dye into a well of dye plate
    dye_plate["A1"].load_liquid(liquid=dye, volume=200)

    # Transfer dye to each destination well (5 ul each)
    for i in range(1, 13):
        p20.pick_up_tip()
        p20.aspirate(5, dye_plate["A1"])
        p20.dispense(5, dest_plate[f"A{i}"])
        p20.drop_tip()

    # Transfer samples to destination (mix with dye)
    for i in range(1, 13):
        p20.pick_up_tip()
        p20.aspirate(15, source_plate[f"A{i}"])
        p20.dispense(15, dest_plate[f"A{i}"])
        p20.drop_tip()
