from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    liquids = {}
    liquids["pcr mix"] = protocol.define_liquid(
        name="pcr mix",
        description="PCR mix for colony PCR",
        display_color="#FF0000"
    )
    for i in range(1, 17):
        liquids[f"colony {i}"] = protocol.define_liquid(
            name=f"colony {i}",
            description=f"Colony {i} resuspension",
            display_color="#000000"
        )
    liquids["water"] = protocol.define_liquid(
        name="water",
        description="Nuclease-free water",
        display_color="#00FFFF"
    )
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    colony_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    # Load pcr mix into tuberack A1
    tuberack["A1"].load_liquid(liquid=liquids["pcr mix"], volume=400)
    # Load colony liquids into colony plate first 16 wells
    for i, well in enumerate(colony_plate.wells()[:16]):
        well.load_liquid(liquid=liquids[f"colony {i+1}"], volume=100)
    # Load water into tuberack A2
    tuberack["A2"].load_liquid(liquid=liquids["water"], volume=100)
    # Distribute 20 ul pcr mix into 16 destination wells
    p20.pick_up_tip()
    for dest_well in plate.wells()[:16]:
        p20.aspirate(20, tuberack["A1"])
        p20.dispense(20, dest_well)
    p20.drop_tip()
    # Add 1 ul of each colony to the corresponding well, mixing after each addition
    for colony_well, dest_well in zip(colony_plate.wells()[:16], plate.wells()[:16]):
        p20.pick_up_tip()
        p20.aspirate(1, colony_well)
        p20.dispense(1, dest_well)
        p20.mix(5, 17, dest_well)
        p20.drop_tip()
    # No-template control: 20 ul pcr mix + 1 ul water in extra well H12
    p20.pick_up_tip()
    p20.aspirate(20, tuberack["A1"])
    p20.dispense(20, plate["H12"])
    p20.aspirate(1, tuberack["A2"])
    p20.dispense(1, plate["H12"])
    p20.mix(5, 17, plate["H12"])
    p20.drop_tip()
