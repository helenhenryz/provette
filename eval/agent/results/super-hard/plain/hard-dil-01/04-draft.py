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
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)  # PBS in A1, waste in A2-A12
    elisa_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 5)

    # Load liquids into tubes and reservoir
    for i, tube in enumerate(tuberack.wells()):
        tube.load_liquid(liquid=serum_liquids[f"serum {i+1}"], volume=1000)  # 1 mL each
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=12000)  # PBS

    # Instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips_300])
    p1000 = protocol.load_instrument("p1000_single_gen2", "left", tip_racks=[tips_1000])

    waste_wells = [reservoir[well] for well in ["A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12"]]
    waste_idx = 0

    # Process each serum
    for i, tube in enumerate(tuberack.wells()):
        # Remove excess serum (950 µL) to waste
        p1000.pick_up_tip()
        p1000.aspirate(950, tube)
        p1000.dispense(950, waste_wells[waste_idx])
        p1000.drop_tip()
        waste_idx = (waste_idx + 1) % len(waste_wells)

        # Add 450 µL PBS
        p1000.pick_up_tip()
        p1000.aspirate(450, reservoir["A1"])
        p1000.dispense(450, tube)
        p1000.drop_tip()

        # Mix (three cycles of 200 µL)
        p300.pick_up_tip()
        for _ in range(3):
            p300.aspirate(200, tube)
            p300.dispense(200, tube)
        p300.drop_tip()

        # Transfer 200 µL (100 µL x2) to ELISA plate
        p300.pick_up_tip()
        p300.aspirate(200, tube)  # draws from the mixed dilution
        p300.dispense(100, elisa_plate.wells()[2*i])
        p300.dispense(100, elisa_plate.wells()[2*i + 1])
        p300.drop_tip()
