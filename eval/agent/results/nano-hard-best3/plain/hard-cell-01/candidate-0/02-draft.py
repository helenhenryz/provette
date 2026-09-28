from opentrons import protocol_api

metadata = {
    "protocolName": "Seed 96-well plate with three cell lines",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", "2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    
    # Define liquids and capture the returned objects
    line1_liquid = protocol.define_liquid(
        name="line 1",
        description="Cell line 1 suspension",
        display_color="#FF0000"
    )
    line2_liquid = protocol.define_liquid(
        name="line 2",
        description="Cell line 2 suspension",
        display_color="#00FF00"
    )
    line3_liquid = protocol.define_liquid(
        name="line 3",
        description="Cell line 3 suspension",
        display_color="#0000FF"
    )
    
    # Load liquids into tubes using the returned objects
    tubes["A1"].load_liquid(liquid=line1_liquid, volume=5000)
    tubes["A2"].load_liquid(liquid=line2_liquid, volume=5000)
    tubes["A3"].load_liquid(liquid=line3_liquid, volume=5000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    rows = ["A","B","C","D","E","F","G","H"]
    
    source_map = {
        1: "A1",
        5: "A2",
        9: "A3"
    }
    
    # Process each column group
    for col_start, source_well in source_map.items():
        # Loop over the 4 columns in this group
        for offset in range(4):
            col = col_start + offset
            # Loop over the 8 rows
            for row in rows:
                well = f"{row}{col}"
                # Pick up a new tip
                p300.pick_up_tip()
                # Aspirate 100 ul from the source well
                p300.aspirate(100, tubes[source_well])
                # Dispense 100 ul into the destination well
                p300.dispense(100, plate[well])
                # Drop the tip
                p300.drop_tip()
