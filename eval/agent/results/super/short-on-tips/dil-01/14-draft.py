from opentrons import protocol_api

metadata = {"protocolName": "1:2 serial dilution drug into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    
    # load liquids
    tuberack["A1"].load_liquid(liquid=drug, volume=500)   # drug stock
    reservoir["A1"].load_liquid(liquid=pbs, volume=15000) # PBS diluent
    
    well_names = [f"A{i+1}" for i in range(12)]  # A1-A12 for dilution
    
    for i, well in enumerate(well_names):
        p300.pick_up_tip()
        # 1. add diluent (PBS) 100 ul
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, plate[well])
        p300.blow_out()
        # 2. transfer in from source 100 ul
        if i == 0:
            src = tuberack["A1"]  # stock
        else:
            src = plate[well_names[i-1]]  # previous well
        p300.aspirate(100, src)
        p300.dispense(100, plate[well])
        p300.blow_out()
        # 3. mix: three cycles of 150 ul
        for _ in range(3):
            p300.aspirate(150, plate[well])
            p300.dispense(150, plate[well])
        p300.blow_out()
        # 4. remove excess 100 ul to waste (back to PBS reservoir)
        p300.aspirate(100, plate[well])
        p300.dispense(100, reservoir["A1"])
        p300.blow_out()
        p300.drop_tip()
    
    # add a blank well (PBS only) at B1 as negative control
    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["B1"])
    p300.drop_tip()
    
