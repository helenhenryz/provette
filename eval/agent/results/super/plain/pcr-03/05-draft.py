import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup master mix + template", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 1)
    tips_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # Pipettes
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tips_1000])
    p20_multi = protocol.load_instrument("p20_multi_gen2", "left", tip_racks=[tips_20])
    
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
    wells_per_tip = 55  # 1000 ul / 18 ul approx
    well_list = [r + c for r in rows for c in cols]
    for i in range(0, len(well_list), wells_per_tip):
        batch = well_list[i:i+wells_per_tip]
        p1000.pick_up_tip()
        vol_needed = len(batch) * 18
        p1000.aspirate(vol_needed, reservoir["A1"])
        for well in batch:
            p1000.dispense(18, dest_plate[well])
        p1000.drop_tip()
    
    # --- Add template using p20_multi column-wise ---
    for c in cols:
        src_wells = [source_plate[r + c] for r in rows]
        dst_wells = [dest_plate[r + c] for r in rows]
        p20_multi.pick_up_tip()
        p20_multi.transfer(
            2,
            src_wells,
            dst_wells,
            mix_after=(3, 10),
            new_tip='never'
        )
        p20_multi.drop_tip()
