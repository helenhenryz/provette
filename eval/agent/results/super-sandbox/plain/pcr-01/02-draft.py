import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup for 8 samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 3)
    
    # Pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    sample_liquids = {}
    for i in range(1, 9):
        liq = protocol.define_liquid(
            name=f"sample {i}",
            description=f"DNA sample {i}",
            display_color="#00FF00"
        )
        sample_liquids[f"sample {i}"] = liq
    
    # Load liquids into wells (starting volumes)
    tube_rack["A1"].load_liquid(master_mix, volume=500)  # master mix
    sample_well_positions = ["B1", "C1", "D1", "A2", "B2", "C2", "D2", "A3"]
    for idx, pos in enumerate(sample_well_positions, start=1):
        tube_rack[pos].load_liquid(sample_liquids[f"sample {idx}"], volume=200)
    
    # Prepare reactions: wells A1-A8 in plate
    dest_wells = [f"A{i+1}" for i in range(8)]  # A1..A8
    
    for idx, well in enumerate(dest_wells, start=1):
        p20.pick_up_tip()
        # Add master mix (20 ul)
        p20.aspirate(20, tube_rack["A1"])
        p20.dispense(20, plate[well])
        # Add sample (5 ul)
        sample_well = tube_rack[sample_well_positions[idx-1]]
        p20.aspirate(5, sample_well)
        p20.dispense(5, plate[well])
        p20.drop_tip()
