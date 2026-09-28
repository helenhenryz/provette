import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 8 samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)

    # Pipettes
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tiprack])
    p20_single = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])

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
            display_color=0x00FF00 >> (i*2)  # just varied
        )
        samples[f"sample {i}"] = liq

    # Load liquids into sources
    tuberack["A1"].load_liquid(liquid=master_mix, volume=1500)  # master mix tube
    for i in range(1, 9):
        tuberack[f"chr(65+(i-1))"]  # placeholder
    # Actually assign sample tubes B1..H1 etc
    sample_positions = ["B1","C1","D1","E1","F1","G1","H1","B2"]  # 8 positions
    for i, pos in enumerate(sample_positions, start=1):
        tuberack[pos].load_liquid(liquid=samples[f"sample {i}"], volume=500)

    # Distribute master mix 20 ul to column 1 (A1-H1) using multi-channel
    p300_multi.pick_up_tip()
    # Aspirate master mix from tube A1
    p300_multi.aspirate(20*8 + 20, tuberack["A1"])  # 8 reactions + a little extra
    # Dispense to each well in column 1
    for col in ["A","B","C","D","E","F","G","H"]:
        well = f"{col}1"
        p300_multi.dispense(20, plate[well])
    p300_multi.drop_tip()

    # Add samples 5 ul each using single channel, new tip per sample
    for i in range(1, 9):
        sample_well = sample_positions[i-1]
        dest_well = f"{chr(64+i)}1"  # A1..H1
        p20_single.pick_up_tip()
        p20_single.aspirate(5, tuberack[sample_well])
        p20_single.dispense(5, plate[dest_well])
        p20_single.drop_tip()
