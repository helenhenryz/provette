from opentrons import protocol_api

metadata = {
    "protocolName": "Serial Dilution and Transfer",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    compound_1 = protocol.define_liquid(
        name="compound 1",
        description="10 mM stock of compound 1",
        display_color="#FF0000"
    )
    compound_2 = protocol.define_liquid(
        name="compound 2",
        description="10 mM stock of compound 2",
        display_color="#00FF00"
    )
    compound_3 = protocol.define_liquid(
        name="compound 3",
        description="10 mM stock of compound 3",
        display_color="#0000FF"
    )
    compound_4 = protocol.define_liquid(
        name="compound 4",
        description="10 mM stock of compound 4",
        display_color="#FFFF00"
    )
    dmso = protocol.define_liquid(
        name="dmso",
        description="Dimethyl sulfoxide",
        display_color="#808080"
    )
    medium = protocol.define_liquid(
        name="medium",
        description="Cell culture medium",
        display_color="#00FFFF"
    )

    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    dms0_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 5)

    # Load liquids into wells
    tubes["A1"].load_liquid(liquid=compound_1, volume=1000)
    tubes["A2"].load_liquid(liquid=compound_2, volume=1000)
    tubes["A3"].load_liquid(liquid=compound_3, volume=1000)
    tubes["A4"].load_liquid(liquid=compound_4, volume=1000)
    dms0_reservoir["A1"].load_liquid(liquid=dmso, volume=1000)
    destination_wells = [
        "A1","A2","A3","A4","A5","A6",
        "B1","B2","B3","B4","B5","B6",
        "C1","C2","C3","C4","C5","C6",
        "D1","D2","D3","D4","D5","D6"
    ]
    for well in destination_wells:
        dest_plate[well].load_liquid(liquid=medium, volume=90)

    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    p300.pick_up_tip()

    # Hardcoded series steps for a 1:3 dilution series (6 points, final volume 60 ul)
    series_steps = [
        {"step_1_add_diluent_ul": 0.0, "step_2_transfer_in_ul": 90.0, "from": "stock"},
        {"step_1_add_diluent_ul": 60.0, "step_2_transfer_in_ul": 30.0, "from": "well 1"},
        {"step_1_add_diluent_ul": 60.0, "step_2_transfer_in_ul": 30.0, "from": "well 2"},
        {"step_1_add_diluent_ul": 60.0, "step_2_transfer_in_ul": 30.0, "from": "well 3"},
        {"step_1_add_diluent_ul": 60.0, "step_2_transfer_in_ul": 30.0, "from": "well 4"},
        {"step_1_add_diluent_ul": 60.0, "step_2_transfer_in_ul": 30.0, "from": "well 5"},
    ]
    last_well_remove_vol = 30.0

    # Mapping of compound number to source plate well names
    compound_to_well_names = {
        1: ["A1","A2","A3","A4","A5","A6"],
        2: ["B1","B2","B3","B4","B5","B6"],
        3: ["C1","C2","C3","C4","C5","C6"],
        4: ["D1","D2","D3","D4","D5","D6"]
    }

    # Set up dilution series for each compound
    for compound_num in range(1,5):
        well_names = compound_to_well_names[compound_num]
        stock_well = "A" + str(compound_num)
        stock_source = tubes[stock_well]
        for i in range(6):
            step = series_steps[i]
            well_name = well_names[i]
            # Add diluent if needed
            add_vol = step["step_1_add_diluent_ul"]
            if add_vol > 0:
                p300.aspirate(add_vol, dms0_reservoir["A1"])
                p300.dispense(add_vol, source_plate[well_name])
            # Transfer in
            transfer_vol = step["step_2_transfer_in_ul"]
            source = step["from"]
            if source == "stock":
                p300.aspirate(transfer_vol, stock_source)
                p300.dispense(transfer_vol, source_plate[well_name])
            else:
                # source is like "well X"
                src_well_number = int(source.split()[1])
                prev_well_name = well_names[src_well_number - 1]
                p300.aspirate(transfer_vol, source_plate[prev_well_name])
                p300.dispense(transfer_vol, source_plate[well_name])
            # Mix
            p300.mix(volume=10, repeats=3)
        # Remove excess from last well
        last_well = well_names[-1]
        p300.aspirate(last_well_remove_vol, source_plate[last_well])

    # Transfer 10 ul from each source well to matching destination well
    all_source_well_names = []
    for compound_num in range(1,5):
        all_source_well_names.extend(compound_to_well_names[compound_num])
    for well_name in all_source_well_names:
        p300.aspirate(10, source_plate[well_name])
        p300.dispense(10, dest_plate[well_name])

    # Drop tip
    p300.drop_tip()
