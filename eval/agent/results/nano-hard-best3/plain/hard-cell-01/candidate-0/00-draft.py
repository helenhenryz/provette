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
    
    # Define liquids
    protocol.define_liquid(
        name="line 1",
        description="Cell line 1 suspension",
        display_color="#FF0000"
    )
    protocol.define_liquid(
        name="line 2",
        description="Cell line 2 suspension",
        display_color="#00FF00"
    )
    protocol.define_liquid(
        name="line 3",
        description="Cell line 3 suspension",
        display_color="#0000FF"
    )
    
    # Load liquids into tubes
    tubes["A1"].load_liquid(liquid="line 1", volume=5000)
    tubes["A2"].load_liquid(liquid="line 2", volume=5000)
    tubes["A3"].load_liquid(liquid="line 3", volume=5000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    rows = ["A","B","C","D","E","F","G","H"]
    
    source_map = {
        1: "A1",
        5: "A2",
        9: "A3"
    }
    
    for col_start, source_well in source_map.items():
        aspirate_vol = 100 * (4 * 8)  # 3200 ul
        p300.pick_up_tip()
        p300.aspirate(aspirate_vol, tubes[source_well])
        for offset in range(4):
            col = col_start + offset
            for row in rows:
                well = f"{row}{col}"
                p300.dispense(100, plate[well])
        p300.drop_tip()
