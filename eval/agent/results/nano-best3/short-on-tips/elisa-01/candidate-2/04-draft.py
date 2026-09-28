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

    # Generate well names for the first 40 wells that are NOT in column 12
    well_names = []
    for row in "ABCDEFGH":
        for col in range(1, 13):
            if col == 12:
                continue  # skip column 12
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

    # Perform serum transfers: one fresh tip per transfer
    for name in well_names:
        src_well = source_plate[name]
        dest_well = dest_plate[name]  # same name in destination plate
        p300.pick_up_tip()
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_well)
        p300.drop_tip()

    # Perform standards transfers: one fresh tip per transfer
    for i in range(8):
        src_well = tube_rack.wells()[i]
        dest_well = dest_plate[f"{chr(65+i)}{12}"]  # A12, B12, ..., H12
        p300.pick_up_tip()
        p300.aspirate(100, src_well)
        p300.dispense(100, dest_well)
        p300.drop_tip()
