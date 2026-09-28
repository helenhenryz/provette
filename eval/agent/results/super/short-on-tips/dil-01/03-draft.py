from opentrons import protocol_api

metadata = {"protocolName": "1:2 serial dilution drug into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)   # for p20
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2) # for p300
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips300])
    
    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    
    # load liquids
    tuberack["A1"].load_liquid(liquid=drug, volume=500)   # drug stock
    reservoir["A1"].load_liquid(liquid=pbs, volume=15000) # PBS
    
    # volumes per well from platemap
    drug_vols = [50.0, 25.0, 12.5, 6.25, 3.12, 1.56, 0.78, 0.39, 0.2, 0.1, 0.05, 0.02]
    pbs_vols = [100 - v for v in drug_vols]
    
    well_names = [f"A{i+1}" for i in range(12)]
    
    def transfer_with_pipette(pipette, src, dst, volume):
        """Transfer volume using pipette, splitting if exceeds pipette max."""
        max_vol = pipette.max_volume
        while volume > 0:
            vol = min(volume, max_vol)
            pipette.aspirate(vol, src)
            pipette.dispense(vol, dst)
            volume -= vol
    
    # PBS tip reuse: pick up once, use for all wells
    p300.pick_up_tip()
    for i, well in enumerate(well_names):
        # drug addition with fresh p20 tip each well
        p20.pick_up_tip()
        if i == 0:
            drug_src = tuberack["A1"]
        else:
            drug_src = plate[well_names[i-1]]
        transfer_with_pipette(p20, drug_src, plate[well], drug_vols[i])
        p20.drop_tip()
        
        # PBS addition with reused p300 tip
        transfer_with_pipette(p300, reservoir["A1"], plate[well], pbs_vols[i])
    p300.drop_tip()
    
    # mixing: use p300 with fresh tip each well
    for well in well_names:
        p300.pick_up_tip()
        p300.mix(5, 80, plate[well])  # 5 cycles of 80 ul
        p300.drop_tip()
    
