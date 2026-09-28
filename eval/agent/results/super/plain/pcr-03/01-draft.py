import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup master mix + template", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # Pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    master_mix = protocol.define_liquid(
        name="master mix",
        description="PCR master mix",
        display_color="#FF0000"
    )
    # Reservoir well A1 contains master mix
    reservoir["A1"].load_liquid(liquid=master_mix, volume=2000)  # enough for 96*18 + overage
    
    # Define each sample liquid
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
    
    # Add master mix to each well with fresh tip each
    for r in rows:
        for c in cols:
            well = r + c
            p20.pick_up_tip()
            p20.aspirate(18, reservoir["A1"])
            p20.dispense(18, dest_plate[well])
            p20.drop_tip()
    
    # Add template to each well with fresh tip each and mix after
    for r in rows:
        for c in cols:
            well = r + c
            p20.pick_up_tip()
            p20.aspirate(2, source_plate[well])
            p20.dispense(2, dest_plate[well])
            # Mix 5 times with 16 ul volume (approx 80% of 20 ul)
            p20.mix(5, 16, dest_plate[well])
            p20.drop_tip()
