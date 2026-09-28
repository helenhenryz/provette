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
    
    # perform 1:2 serial dilution
    for well in well_names:
        # ---- add PBS with fresh tip ----
        p300.pick_up_tip()
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, plate[well])
        p300.blow_out()
        p300.drop_tip()
        # ---- add drug with fresh tip (reuse for mixing) ----
        # determine source
        if well == "A1":
            src = tuberack["A1"]
        else:
            # find previous well in row A
            prev_col = int(well[1:]) - 1
            src = plate[f"A{prev_col}"]
        p300.pick_up_tip()
        p300.aspirate(50, src)
        p300.dispense(50, plate[well])
        p300.blow_out()
        # mix using same tip
        p300.mix(3, 70, plate[well])
        p300.drop_tip()
    
    # add a blank well (PBS only) at B1 as negative control
    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["B1"])
    p300.drop_tip()
    
