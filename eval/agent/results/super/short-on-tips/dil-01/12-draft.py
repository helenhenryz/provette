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
    
    # perform dilution series as per dilution_series output:
    # for each well: add 100 ul PBS, transfer 100 ul from source, mix
    # after all wells, remove 100 ul from last well to waste
    
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
        # 3. mix
        p300.mix(3, 150, plate[well])  # 3 cycles of 150 ul
        p300.drop_tip()
    
    # remove excess from last well (100 ul) to waste
    p300.pick_up_tip()
    p300.aspirate(100, plate[well_names[-1]])
    p300.dispense(100, reservoir["A1"])  # waste back into PBS reservoir (or could use waste well)
    p300.drop_tip()
    
