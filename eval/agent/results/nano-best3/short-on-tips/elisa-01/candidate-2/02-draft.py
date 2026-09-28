from opentrons import protocol_api

metadata = {
    "protocolName": "ELISA Plate Transfer",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    dest_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 1, label='ELISA Plate')
    source_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 2)
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 3)
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 4)

    # Define liquids and store them
    liquid_defs = {}

    # Define standards 1-8
    for i in range(1, 9):
        liquid_defs[f"standard {i}"] = protocol.define_liquid(
            name=f"standard {i}",
            description=f"Standard {i}",
            display_color="#FF0000"
        )

    # Define serums 1-40
    for i in range(1, 41):
        liquid_defs[f"serum {i}"] = protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum {i}",
            display_color="#0000FF"
        )

    # Generate well names for the first 40 wells (row-major order)
    well_names = []
    for row in "ABCDEFGH":
        for col in range(1, 13):
            well_names.append(f"{row}{col}")
            if len(well_names) == 40:
                break
        if len(well_names) == 40:
            break

    # Load serum liquids into source plate wells
    for i, name in enumerate(well_names):
        serum_name = f"serum {i+1}"
        source_plate[name].load_liquid(liquid=liquid_defs[serum_name], volume=200)

    # Load standards into tube rack wells (first 8 wells)
    for i, well in enumerate(tube_rack.wells()[:8]):
        std_name = f"standard {i+1}"
        well.load_liquid(liquid=liquid_defs[std_name], volume=200)

    # Load pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips])

    # Create transfer list
    transfers = []

    # Serum transfers: map each well name to source and destination wells
    for name in well_names:
        src_well = source_plate[name]
        dest_well = dest_plate[name]  # same name in destination plate
        transfers.append((src_well, dest_well, 100))

    # Standards transfers: map standard i to column 12 wells A12-H12
    for i in range(8):
        src_well = tube_rack.wells()[i]
        dest_well = dest_plate[f"{chr(65+i)}{12}"]  # A12, B12, ..., H12
        transfers.append((src_well, dest_well, 100))

    # Perform transfers
    p300.pick_up_tip()
    for src, dest, vol in transfers:
        p300.aspirate(vol, src)
        p300.dispense(vol, dest)
    p300.drop_tip()
