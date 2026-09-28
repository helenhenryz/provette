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

    # Define liquids: standards 1-8
    for i in range(1, 9):
        protocol.define_liquid(
            name=f"standard {i}",
            description=f"Standard {i}",
            display_color="#FF0000"
        )
    # Define liquids: serums 1-40
    for i in range(1, 41):
        protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum {i}",
            display_color="#0000FF"
        )

    # Load liquids into source plate and tube rack
    # Serum samples: first 40 wells of source plate
    for i, well in enumerate(source_plate.wells()[:40]):
        serum_name = f"serum {i+1}"
        well.load_liquid(liquid=serum_name, volume=200)

    # Standards: first 8 wells of tube rack
    for i, well in enumerate(tube_rack.wells()[:8]):
        std_name = f"standard {i+1}"
        well.load_liquid(liquid=std_name, volume=200)

    # Load pipette
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips])

    # Create transfer list
    transfers = []

    # Serum transfers: source well -> destination well with same name
    for source_well in source_plate.wells()[:40]:
        dest_well = dest_plate[source_well.name]
        transfers.append((source_well, dest_well, 100))

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
