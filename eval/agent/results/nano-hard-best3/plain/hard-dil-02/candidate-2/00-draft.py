from opentrons import protocol_api

metadata = {
    "protocolName": "1:3 Serial Dilution Assay",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Define liquids
    protocol.define_liquid(name="compound 1", description="10 mM stock of compound 1", display_color="#FF0000")
    protocol.define_liquid(name="compound 2", description="10 mM stock of compound 2", display_color="#FF6600")
    protocol.define_liquid(name="compound 3", description="10 mM stock of compound 3", display_color="#FFAA00")
    protocol.define_liquid(name="compound 4", description="10 mM stock of compound 4", display_color="#FFCC00")
    protocol.define_liquid(name="dmso", description="Pure DMSO", display_color="#00FFFF")
    protocol.define_liquid(name="medium", description="Cell culture medium", display_color="#00FF00")

    # Load liquids into wells
    tube_rack["A1"].load_liquid(liquid="compound 1", volume=500)
    tube_rack["A2"].load_liquid(liquid="compound 2", volume=500)
    tube_rack["A3"].load_liquid(liquid="compound 3", volume=500)
    tube_rack["A4"].load_liquid(liquid="compound 4", volume=500)
    reservoir["A1"].load_liquid(liquid="dmso", volume=1500)
    for row in ["A","B","C","D"]:
        for col in range(1,7):
            well = dest_plate[row + str(col)]
            well.load_liquid(liquid="medium", volume=90)

    # Load the p300 pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])

    # Process each compound (rows A-D)
    for idx, row in enumerate(["A","B","C","D"]):
        compound_num = idx + 1
        source_tube_well = tube_rack["A" + str(compound_num)]
        series_wells = [row + str(col) for col in range(1,7)]

        for i, well_name in enumerate(series_wells):
            well = source_plate[well_name]

            if i == 0:  # First well: add stock
                p300.pick_up_tip()
                p300.aspirate(90, source_tube_well)
                p300.dispense(90, well)
                # Mix
                p300.aspirate(5, well)
                p300.dispense(5, well)
                p300.aspirate(5, well)
                p300.dispense(5, well)
                p300.drop_tip()
            else:
                # Add diluent (60 ul DMSO) and transfer 30 ul from previous well
                p300.pick_up_tip()
                p300.aspirate(60, reservoir["A1"])
                p300.dispense(60, well)
                # Transfer from previous well
                prev_well_name = series_wells[i-1]
                prev_well = source_plate[prev_well_name]
                p300.aspirate(30, prev_well)
                p300.dispense(30, well)
                # Mix
                p300.aspirate(5, well)
                p300.dispense(5, well)
                p300.aspirate(5, well)
                p300.dispense(5, well)
                p300.drop_tip()
                # If last well, remove 30 ul to waste
                if i == 5:  # last well index (0-indexed)
                    p300.pick_up_tip()
                    p300.aspirate(30, well)
                    p300.drop_tip()

    # Transfer 10 ul from each source well to the corresponding destination well
    for row in ["A","B","C","D"]:
        for col in range(1,7):
            src_well_name = row + str(col)
            src_well = source_plate[src_well_name]
            dest_well = dest_plate[src_well_name]
            p300.pick_up_tip()
            p300.aspirate(10, src_well)
            p300.dispense(10, dest_well)
            p300.drop_tip()
