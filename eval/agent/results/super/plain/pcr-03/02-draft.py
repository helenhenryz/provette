import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup master mix + template", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    tips_300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # Pipettes
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips_1000])
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips_300])
    
    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)  # sufficient
    
    rows = ["A","B","C","D","E","F","G","H"]
    cols = [str(i) for i in range(1,13)]
    for r in rows:
        for c in cols:
            well_name = r + c
            liquid = protocol.define_liquid(
                name=f"sample_{well_name}",
                description=f"Template sample {well_name}",
                display_color="#00FF00"
            )
            source_plate[well_name].load_liquid(liquid=liquid, volume=100)
    
    # --- Add master mix using p1000 single ---
    # Calculate number of wells per tip: 1000 ul / 18 ul ≈ 55 wells
    wells_per_tip = 55
    well_list = [r + c for r in rows for c in cols]
    tip_count = 0
    for i in range(0, len(well_list), wells_per_tip):
        batch = well_list[i:i+wells_per_tip]
        p1000.pick_up_tip()
        # Aspirate enough volume for this batch (+ small excess for safety)
        vol_needed = len(batch) * 18
        p1000.aspirate(vol_needed, reservoir["A1"])
        for well in batch:
            p1000.dispense(18, dest_plate[well])
        p1000.drop_tip()
        tip_count += 1
    
    # --- Add template using p300 multi row-wise ---
    for r in rows:
        # Prepare list of source wells for this row
        src_wells = [source_plate[r + str(c)] for c in range(1,13)]
        dst_wells = [dest_plate[r + str(c)] for c in range(1,13)]
        p300_multi.pick_up_tip()
        # Aspirate 2 ul from each source well in the row
        p300_multi.aspirate(2, src_wells)
        # Dispense 2 ul to each destination well in the row
        p300_multi.dispense(2, dst_wells)
        # Mix each well after dispensing
        for well in dst_wells:
            p300_multi.mix(3, 16, well)
        p300_multi.drop_tip()
