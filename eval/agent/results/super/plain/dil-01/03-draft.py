from opentrons import protocol_api

metadata = {"protocolName": "1:2 serial dilution drug across row A", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Liquids
    pbs = protocol.define_liquid(
        name="pbs",
        description="phosphate buffered saline",
        display_color="#00FF00"
    )
    drug = protocol.define_liquid(
        name="drug",
        description="drug stock solution",
        display_color="#FF0000"
    )

    # Initial volumes in sources (add a little extra)
    reservoir["A1"].load_liquid(liquid=pbs, volume=1500)  # PBS
    tube_rack["A1"].load_liquid(liquid=drug, volume=200)   # drug stock

    # Optional blank well (PBS only) to satisfy negative control requirement
    plate["B1"].load_liquid(liquid=pbs, volume=100)  # blank, not used in dilution

    # Waste well (use reservoir A12)
    waste = reservoir["A12"]

    # Perform serial dilution
    for i in range(12):
        col = i + 1
        dest_well = plate[f"A{col}"]
        # Step 1: add diluent (PBS) 100 ul
        p300.pick_up_tip()
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, dest_well)
        p300.drop_tip()

        # Step 2: transfer in from source
        if i == 0:
            src = tube_rack["A1"]  # stock
        else:
            src = plate[f"A{col-1}"]  # previous well
        p300.pick_up_tip()
        p300.aspirate(100, src)
        p300.dispense(100, dest_well)
        # Mix after combining liquids to avoid layering before next draw
        p300.mix(3, 150, dest_well)
        p300.drop_tip()

    # After loop, remove excess from last well (well A12) 100 ul to waste
    p300.pick_up_tip()
    p300.aspirate(100, plate["A12"])
    p300.dispense(100, waste)
    p300.drop_tip()
