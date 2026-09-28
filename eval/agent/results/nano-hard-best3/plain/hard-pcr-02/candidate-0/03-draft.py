from opentrons import protocol_api

metadata = {"protocolName": "PrepPCR", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load tip racks
    tips_20ul = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_200ul = protocol.load_labware("opentrons_96_tiprack_300ul", 2)

    # Load plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

    # Load tube rack for all liquids (mix, water, templates)
    liquids_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)

    # Load pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips_20ul])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_200ul])

    # Define liquids and capture the returned objects
    mix_liquid = protocol.define_liquid(
        name="mix",
        description="2x master mix",
        display_color="#FF0000"
    )
    water_liquid = protocol.define_liquid(
        name="water",
        description="nuclease-free water",
        display_color="#0000FF"
    )
    template_liquids = {}
    for i in range(1, 9):
        template_liquids[f"template {i}"] = protocol.define_liquid(
            name=f"template {i}",
            description=f"Template {i}",
            display_color="#808080"
        )

    # Load liquids into source wells in the tube rack
    liquids_rack["C1"].load_liquid(liquid=mix_liquid, volume=500)
    liquids_rack["C2"].load_liquid(liquid=water_liquid, volume=500)
    template_well_names = ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2"]
    for i, well_name in enumerate(template_well_names):
        liquids_rack[well_name].load_liquid(
            liquid=template_liquids[f"template {i+1}"],
            volume=20
        )

    # Destination wells
    dest_well_names = [f"A{i+1}" for i in range(8)]

    # Perform transfers for each of the 8 reactions
    for i, dest_name in enumerate(dest_well_names):
        # Transfer 50 ul of mix
        p300.pick_up_tip()
        p300.aspirate(50, liquids_rack["C1"].bottom(0.5))
        p300.dispense(50, plate[dest_name])
        p300.drop_tip()

        # Transfer 42 ul of water
        p300.pick_up_tip()
        p300.aspirate(42, liquids_rack["C2"].bottom(0.5))
        p300.dispense(42, plate[dest_name])
        p300.drop_tip()

        # Transfer 8 ul of template
        template_source_well_name = template_well_names[i]
        p20.pick_up_tip()
        p20.aspirate(8, liquids_rack[template_source_well_name])
        p20.dispense(8, plate[dest_name])
        p20.drop_tip()
