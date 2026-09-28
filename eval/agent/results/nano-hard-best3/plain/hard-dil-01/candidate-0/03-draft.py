from opentrons import protocol_api

metadata = {
    "protocolName": "Dilute 24 serum samples 1 in 10 and transfer duplicates",
    "apiLevel": "2.19"
}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    dilution_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 3)
    elisa_plate = protocol.load_labware("corning_384_wellplate_112ul_flat", 4)
    tips = protocol.load_labware("opentrons_96_tiprack_1000ul", 5)
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips])

    # Define liquids and load them into source wells
    tuberack_well_list = tuberack.wells()
    for i in range(24):
        serum_liquid = protocol.define_liquid(name=f"serum {i+1}", description=f"Serum sample {i+1}", display_color="#FF0000")
        well = tuberack_well_list[i]
        well.load_liquid(liquid=serum_liquid, volume=50)

    # Define PBS liquid and load into reservoir
    pbs_liquid = protocol.define_liquid(name="pbs", description="Phosphate-buffered saline", display_color="#0000FF")
    reservoir["A1"].load_liquid(liquid=pbs_liquid, volume=2000)

    # Get source wells (first 24 wells of dilution plate)
    source_wells = dilution_plate.wells()[:24]

    # Get destination wells (first 48 wells of ELISA plate)
    dest_wells = elisa_plate.wells()[:48]

    # Perform transfers for each serum sample
    for i in range(24):
        p1000.pick_up_tip()
        # Aspirate 50 ul serum from the tube rack well
        serum_well = tuberack_well_list[i]
        p1000.aspirate(50, serum_well)
        # Dispense into the corresponding source well in dilution plate
        p1000.dispense(50, source_wells[i])
        # Aspirate 450 ul PBS from reservoir
        p1000.aspirate(450, reservoir["A1"])
        # Dispense PBS into the same source well to mix
        p1000.dispense(450, source_wells[i])
        # Transfer 100 ul to first destination well
        p1000.aspirate(100, source_wells[i])
        p1000.dispense(100, dest_wells[2*i])
        # Transfer 100 ul to second destination well
        p1000.aspirate(100, source_wells[i])
        p1000.dispense(100, dest_wells[2*i+1])
        p1000.drop_tip()
