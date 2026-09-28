import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 8 samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)

    # Pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack])
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    samples = {}
    for i in range(1, 9):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"DNA sample {i}",
            display_color="#00FF00"
        )
        samples[f"sample {i}"] = liq

    # Load liquids into sources
    tuberack["A1"].load_liquid(liquid=master_mix, volume=1500)  # master mix tube
    # Place samples in tubes B1, C1, D1, A2, B2, C2, D2, A3
    sample_positions = ["B1", "C1", "D1", "A2", "B2", "C2", "D2", "A3"]
    for i, pos in enumerate(sample_positions, start=1):
        tuberack[pos].load_liquid(liquid=samples[f"sample {i}"], volume=500)

    # Distribute master mix 20 ul to column 1 (A1-H1) using single channel, one tip
    p300.pick_up_tip()
    # Aspirate exactly 20 ul * 8 wells
    p300.aspirate(20 * 8, tuberack["A1"])
    for letter in ["A","B","C","D","E","F","G","H"]:
        well = f"{letter}1"
        p300.dispense(20, plate[well])
    p300.drop_tip()

    # Add samples 5 ul each using single channel, new tip per sample
    sample_locations = ["B1","C1","D1","A2","B2","C2","D2","A3"]
    dest_wells = ["A1","B1","C1","D1","E1","F1","G1","H1"]
    for src, dst in zip(sample_locations, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(5, tuberack[src])
        p20.dispense(5, plate[dst])
        p20.drop_tip()
