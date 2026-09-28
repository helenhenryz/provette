from opentrons import protocol_api

metadata = {"protocolName": "Serial Dilution Drug into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    pbs = protocol.define_liquid(name="pbs", description="PBS", display_color="#00FF00")
    
    tubes["A1"].load_liquid(liquid=drug, volume=2000)
    reservoir["A1"].load_liquid(liquid=pbs, volume=2000)
    
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    dest_wells = [plate["A1"], plate["A2"], plate["A3"], plate["A4"], plate["A5"], plate["A6"], plate["A7"], plate["A8"], plate["A9"], plate["A10"], plate["A11"], plate["A12"]]
    
    p300.pick_up_tip()
    
    for i, well in enumerate(dest_wells):
        if i == 0:
            p300.aspirate(50, tubes["A1"])
            p300.dispense(50, well)
            p300.aspirate(50, reservoir["A1"])
            p300.dispense(50, well)
            p300.mix(5, 100)
        else:
            p300.aspirate(50, dest_wells[i-1])
            p300.dispense(50, well)
            p300.aspirate(50, reservoir["A1"])
            p300.dispense(50, well)
            p300.mix(5, 100)
    
    p300.drop_tip()
