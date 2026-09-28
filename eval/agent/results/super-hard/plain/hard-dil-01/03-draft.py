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
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 5)

    # Load liquids into tubes and reservoir
    for i, tube in enumerate(tuberack.wells()):
        tube.load_liquid(liquid=serum_liquids[f"serum {i+1}"], volume=1000)  # 1 mL each
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=12000)  # enough PBS

    # Instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips_1000])

    # Process each serum
    for i, tube in enumerate(tuberack.wells()):
        # Add 450 µL PBS to the serum tube
        p1000.pick_up_tip()
        p1000.aspirate(450, reservoir["A1"])
        p1000.dispense(450, tube)
        p1000.drop_tip()

        # Mix briefly (aspirate/dispense 200 µL three times)
        p300.pick_up_tip()
        for _ in range(3):
            p300.aspirate(200, tube)
            p300.dispense(200, tube)
        p300.drop_tip()

        # Transfer 200 µL (100 µL x2) to ELISA plate wells
        p300.pick_up_tip()
        p300.aspirate(200, tube)  # takes 100 µL for each duplicate
        # Dispense to first well
        p300.dispense(100, elisa_plate.wells()[2*i])
        # Dispense to second well
        p300.dispense(100, elisa_plate.wells()[2*i + 1])
        p300.drop_tip()
