from opentrons import protocol_api

metadata = {"protocolName": "ELISA sample addition", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, label="ELISA Source")
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3, label="ELISA Coated")
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # define liquids
    # standards
    std_names = [f"standard {i}" for i in range(1, 9)]
    for name in std_names:
        protocol.define_liquid(name=name, description="ELISA standard", display_color="#FF0000")
    # sera
    serum_names = [f"serum {i}" for i in range(1, 41)]
    for name in serum_names:
        protocol.define_liquid(name=name, description="Serum sample", display_color="#00FF00")

    # load liquids into source wells (sera) and tube wells (standards)
    # sera placed in source plate wells A1..H1.. etc mapping 1-40 to A1..J4? easier: fill sequentially row-wise
    serum_wells = [well for row in source_plate.rows() for well in row][:40]
    for well, name in zip(serum_wells, serum_names):
        well.load_liquid(name, 200)  # starting volume

    # standards in tube rack A1..H1? we have 24 wells, use first 8
    std_wells = [tube_rack.wells_by_name()[f"{chr(ord('A')+i)}1") for i in range(8)]
    for well, name in zip(std_wells, std_names):
        well.load_liquid(name, 500)

    # destination wells for sera: match same well names as source
    dest_serum_wells = [dest_plate.wells_by_name()[well.get_name()] for well in serum_wells]

    # transfer sera
    for src, dst in zip(serum_wells, dest_serum_wells):
        p300.pick_up_tip()
        p300.aspirate(100, src)
        p300.dispense(100, dst)
        p300.drop_tip()

    # destination wells for standards: column 12, rows A-H
    std_dest_wells = [dest_plate.wells_by_name()[f"{chr(ord('A')+i)}12") for i in range(8)]

    # transfer standards
    for src, dst in zip(std_wells, std_dest_wells):
        p300.pick_up_tip()
        p300.aspirate(100, src)
        p300.dispense(100, dst)
        p300.drop_tip()
