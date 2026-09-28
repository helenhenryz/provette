import json
from opentrons import protocol_api

metadata = {"protocolName": "ELISA sample addition", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1, label="serum_source")
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, label="ELISA_coated")
    std_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3, label="standard_tubes")
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 4)

    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # Define liquids
    liquids = []
    for i in range(1, 41):
        liquids.append((f"serum {i}", f"#{(i*7)%256:02x}{(i*13)%256:02x}{(i*29)%256:02x}"))
    for i in range(1, 9):
        liquids.append((f"standard {i}", f"#{(i*31)%256:02x}{(i*37)%256:02x}{(i*41)%256:02x}"))
    # Optional buffer/waste
    protocol.define_liquid(name="buffer", description="assay buffer", display_color="#00FF00")
    # Load liquids into source wells and tubes
    # Sera
    for i, well_name in enumerate([
        "A1","B1","C1","D1","E1","F1","G1","H1",
        "A2","B2","C2","D2","E2","F2","G2","H2",
        "A3","B3","C3","D3","E3","F3","G3","H3",
        "A4","B4","C4","D4","E4","F4","G4","H4",
        "A5","B5","C5","D5","E5","F5","G5","H5"
    ], start=1):
        src = source_plate[well_name]
        src.load_liquid(liquid=protocol.define_liquid(
            name=f"serum {i}",
            description=f"Serum sample {i}",
            display_color=f"#{(i*7)%256:02x}{(i*13)%256:02x}{(i*29)%256:02x}"
        ), volume=200)  # starting volume
    # Standards in tubes A1-H1 of rack (8 tubes)
    std_wells = ["A1","B1","C1","D1","E1","F1","G1","H1"]
    for i, well_name in enumerate(std_wells, start=1):
        tube = std_rack[well_name]
        tube.load_liquid(liquid=protocol.define_liquid(
            name=f"standard {i}",
            description=f"Standard {i}",
            display_color=f"#{(i*31)%256:02x}{(i*37)%256:02x}{(i*41)%256:02x}"
        ), volume=200)

    # Transfer sera
    src_wells = [
        "A1","B1","C1","D1","E1","F1","G1","H1",
        "A2","B2","C2","D2","E2","F2","G2","H2",
        "A3","B3","C3","D3","E3","F3","G3","H3",
        "A4","B4","C4","D4","E4","F4","G4","H4",
        "A5","B5","C5","D5","E5","F5","G5","H5"
    ]
    dst_wells = src_wells[:]  # same positions
    for src, dst in zip(src_wells, dst_wells):
        p300.pick_up_tip()
        p300.aspirate(100, source_plate[src])
        p300.dispense(100, dest_plate[dst])
        p300.drop_tip()

    # Transfer standards to column 12 rows A-H
    std_dst = ["A12","B12","C12","D12","E12","F12","G12","H12"]
    for i, (src_well, dst_well) in enumerate(zip(std_wells, std_dst), start=1):
        p300.pick_up_tip()
        p300.aspirate(100, std_rack[src_well])
        p300.dispense(100, dest_plate[dst_well])
        p300.drop_tip()
