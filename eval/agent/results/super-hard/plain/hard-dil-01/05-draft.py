from opentrons import protocol_api

metadata = {"protocolName": "Serum dilution and ELISA transfer", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    serum_liquids = {}
    for i in range(1, 25):
        name = f"serum {i}"
        serum_liquids[name] = protocol.define_liquid(
            name=name,
            description=f"Serum sample {i}",
            display_color="#FF0000"
        )
    pbs_liquid = protocol.define_liquid(
        name="pbs",
        description="Phosphate buffered saline",
        display_color="#00FF00"
    )

    # Load labware
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)  # PBS in A1
    intermediate_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 6)

    # Load liquids into tubes and reservoir
    for i, tube in enumerate(tuberack.wells()):
        tube.load_liquid(liquid=serum_liquids[f"serum {i+1}"], volume=1000)  # 1 mL each
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=5000)  # enough PBS (48*180=8640? wait compute: 24 sera *180 = 4320 µL. So 5 mL enough)

    # Instruments
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips_20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips_300])

    # Process each serum
    for i, tube in enumerate(tuberack.wells()):
        intermediate_well = intermediate_plate.wells()[i]

        # Add 20 µL serum
        p20.pick_up_tip()
        p20.aspirate(20, tube)
        p20.dispense(20, intermediate_well)
        p20.drop_tip()

        # Add 180 µL PBS
        p300.pick_up_tip()
        p300.aspirate(180, reservoir["A1"])
        p300.dispense(180, intermediate_well)
        p300.drop_tip()

        # Mix
        p300.pick_up_tip()
        for _ in range(3):
            p300.aspirate(150, intermediate_well)
            p300.dispense(150, intermediate_well)
        p300.drop_tip()

        # Transfer 200 µL total (100 µL x2) to ELISA plate
        p300.pick_up_tip()
        p300.aspirate(200, intermediate_well)
        p300.dispense(100, elisa_plate.wells()[2*i])
        p300.dispense(100, elisa_plate.wells()[2*i + 1])
        p300.drop_tip()
