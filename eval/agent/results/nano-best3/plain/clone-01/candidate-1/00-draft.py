from opentrons import protocol_api

metadata = {\"protocolName\": \"Restriction Digests\", \"apiLevel\": \"2.19\"}

def run(protocol: protocol_api.ProtocolContext):
    tip_rack = protocol.load_labware(\"opentrons_96_tiprack_20ul\", 1)
    plate = protocol.load_labware(\"biorad_96_wellplate_200ul_pcr\", 2)
    temp_mod = protocol.load_module(\"temperature module gen2\", 3)
    block = temp_mod.load_labware(\"opentrons_24_aluminumblock_nest_1.5ml_snapcap\")
    p20 = protocol.load_instrument(\"p20_single_gen2\", \"right\", tip_racks=[tip_rack])

    plasmid_1 = protocol.define_liquid(name=\"plasmid 1\", description=\"Plasmid 1\", display_color=\"#FF0000\")
    plasmid_2 = protocol.define_liquid(name=\"plasmid 2\", description=\"Plasmid 2\", display_color=\"#FF0101\")
    plasmid_3 = protocol.define_liquid(name=\"plasmid 3\", description=\"Plasmid 3\", display_color=\"#FF0202\")
    plasmid_4 = protocol.define_liquid(name=\"plasmid 4\", description=\"Plasmid 4\", display_color=\"#FF0303\")
    plasmid_5 = protocol.define_liquid(name=\"plasmid 5\", description=\"Plasmid 5\", display_color=\"#FF0404\")
    plasmid_6 = protocol.define_liquid(name=\"plasmid 6\", description=\"Plasmid 6\", display_color=\"#FF0505\")
    plasmid_7 = protocol.define_liquid(name=\"plasmid 7\", description=\"Plasmid 7\", display_color=\"#FF0606\")
    plasmid_8 = protocol.define_liquid(name=\"plasmid 8\", description=\"Plasmid 8\", display_color=\"#FF0707\")
    plasmid_9 = protocol.define_liquid(name=\"plasmid 9\", description=\"Plasmid 9\", display_color=\"#FF0808\")
    plasmid_10 = protocol.define_liquid(name=\"plasmid 10\", description=\"Plasmid 10\", display_color=\"#FF0909\")
    plasmid_11 = protocol.define_liquid(name=\"plasmid 11\", description=\"Plasmid 11\", display_color=\"#FF0A0A\")
    plasmid_12 = protocol.define_liquid(name=\"plasmid 12\", description=\"Plasmid 12\", display_color=\"#FF0B0B\")
    water = protocol.define_liquid(name=\"water\", description=\"Water\", display_color=\"#0000FF\")
    buffer = protocol.define_liquid(name=\"buffer\", description=\"Buffer\", display_color=\"#00FF00\")
    enzyme = protocol.define_liquid(name=\"enzyme\", description=\"Enzyme\", display_color=\"#FFFF00\")

    # Load plasmids into block column A
    for i in range(1, 13):
        plasmid_var = globals()[f\"plasmid_{i}\"]
        block[f\"A{i}\"].load_liquid(liquid=plasmid_var, volume=100)
    # Load buffer, enzyme, water
    block[\"B1\"].load_liquid(liquid=buffer, volume=100)
    block[\"B2\"].load_liquid(liquid=enzyme, volume=50)
    block[\"B3\"].load_liquid(liquid=water, volume=200)

    # Pick up tip
    p20.pick_up_tip()
    # Loop over 12 reactions
    for i in range(1, 13):
        # Add plasmid (5 ul)
        p20.aspirate(5, block[f\"A{i}\"])
        p20.dispense(5, plate[f\"A{i}\"])
        # Add buffer (2 ul)
        p20.aspirate(2, block[\"B1\"])
        p20.dispense(2, plate[f\"A{i}\"])
        # Add enzyme (1 ul)
        p20.aspirate(1, block[\"B2\"])
        p20.dispense(1, plate[f\"A{i}\"])
        # Add water (12 ul)
        p20.aspirate(12, block[\"B3\"])
        p20.dispense(12, plate[f\"A{i}\"])
        # Mix
        p20.mix(5, 10, plate[f\"A{i}\"])
    # Drop tip
    p20.drop_tip()
