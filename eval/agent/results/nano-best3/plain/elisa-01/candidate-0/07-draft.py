from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA plate filling",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    dest_plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 3, label="ELISA")
    standards_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids and load them into source wells
    # Use wells that do not end with "12" to avoid conflict with standard destinations
    serum_wells = [
        "A1","A2","A3","A4","A5","A6","A7","A9","A11",
        "B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11",
        "C1","C2","C3","C4","C5","C6","C7","C8","C9","C10","C11",
        "D1","D2","D3","D4","D5","D6","D7","D8","D9","D10","D11"
    ]
    # Load serum liquids into source plate wells
    for i, well in enumerate(serum_wells, start=1):
        serum_liquid = protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum sample {i}",
            display_color="#0000FF"
        )
        source_plate[well].load_liquid(
            liquid=serum_liquid,
            volume=100
        )

    # Map standard number to tube rack well
    standard_well_map = {
        1: "A1",
        2: "A2",
        3: "A3",
        4: "A4",
        5: "A6",
        6: "B1",
        7: "B2"
    }
    # Load standard liquids into tube rack wells
    for i in range(1, 9):
        std_liquid = protocol.define_liquid(
            name=f"standard {i}",
            description=f"Standard {i}",
            display_color="#FF0000"
        )
        standards_rack[standard_well_map[i]].load_liquid(
            liquid=std_liquid,
            volume=100
        )

    # Transfer serum samples to matching wells in destination plate
    for well in serum_wells:
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[well])
        p300.dispense(100, dest_plate[well])
        p300.drop_tip()

    # Transfer standards to column 12 of destination plate
    for i in range(1, 9):
        src_well = standard_well_map[i]
        dest_well = f"{chr(64 + i)}12"
        p300.pick_up_tip()
        p300.aspirate(100, standards_rack[src_well])
        p300.dispense(100, dest_plate[dest_well])
        p300.drop_tip()
