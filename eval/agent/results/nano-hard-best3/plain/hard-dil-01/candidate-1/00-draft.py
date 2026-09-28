from opentrons import protocol_api

metadata = {
    "protocolName": "Dilute 24 serum samples 1 in 10 and transfer duplicates",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    pbs_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    dil_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)
    elisa_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 5)
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tip_racks])

    # Define liquids
    for i in range(1, 25):
        serum_name = f"serum {i}"
        protocol.define_liquid(
            name=serum_name,
            description=f"Serum sample {i}",
            display_color="#FF0000"
        )
        # Determine well name in tube rack
        if i <= 6:
            well_name = f"A{i}"
        elif i <= 12:
            well_name = f"B{i-6}"
        elif i <= 18:
            well_name = f"C{i-12}"
        else:
            well_name = f"D{i-18}"
        # Load 1500 µL of serum into the well
        tubes[well_name].load_liquid(liquid=serum_name, volume=1500)

    # Define PBS
    protocol.define_liquid(
        name="pbs",
        description="Phosphate Buffered Saline",
        display_color="#0000FF"
    )
    # Load 12000 µL of PBS into reservoir well A1
    pbs_reservoir["A1"].load_liquid(liquid="pbs", volume=12000)

    # Generate source well names in order (A1-A6, B1-B6, C1-C6, D1-D6)
    source_well_names = []
    for row in ["A", "B", "C", "D"]:
        for col in range(1, 7):
            source_well_names.append(row + str(col))

    # Get destination wells in dilution plate (first 24 wells)
    dil_dest_wells = list(dil_plate.wells())[:24]

    # Fill dilution plate
    for i in range(24):
        p1000.pick_up_tip()
        # Aspirate 50 µL from serum
        p1000.aspirate(50, tubes[source_well_names[i]])
        # Aspirate 450 µL from PBS reservoir
        p1000.aspirate(450, pbs_reservoir["A1"])
        # Dispense 500 µL into dilution well
        p1000.dispense(500, dil_dest_wells[i])
        p1000.drop_tip()

    # Get list of destination wells in ELISA plate (first 48 wells)
    elisa_dest_wells = list(elisa_plate.wells())[:48]

    # Transfer 100 µL from each dilution well to duplicate wells in ELISA plate
    for i in range(24):
        p1000.pick_up_tip()
        # Aspirate 100 µL from dilution well
        p1000.aspirate(100, dil_dest_wells[i])
        # Dispense 100 µL to first duplicate well
        p1000.dispense(100, elisa_dest_wells[2*i])
        # Dispense 100 µL to second duplicate well
        p1000.dispense(100, elisa_dest_wells[2*i+1])
        p1000.drop_tip()
