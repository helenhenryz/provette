import json
from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digest Setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # temperature module
    temp_mod = protocol.load_module("temperature module gen2", "1")
    # tubes on temp block
    tuberack = temp_mod.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap")
    # tip rack
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "2")
    # destination PCR plate
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "3")
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # define liquids
    plasmid_names = [f"plasmid {i}" for i in range(1, 13)]
    liquids = plasmid_names + ["water", "buffer", "enzyme"]
    liquid_objs = {}
    for name in liquids:
        liquid_objs[name] = protocol.define_liquid(
            name=name,
            description=f"{name} solution",
            display_color="#FFFFFF" if name != "water" else "#0000FF"
        )
    
    # load initial volumes (realistic)
    plasmid_well_names = ['A1','A2','A3','A4','A5','A6','B1','B2','B3','B4','B5','B6']
    for i, name in enumerate(plasmid_names):
        tuberack[plasmid_well_names[i]].load_liquid(liquid_objs[name], volume=100)  # 100 ul each plasmid
    tuberack['A7'].load_liquid(liquid_objs["water"], volume=1000)   # 1 ml water
    tuberack['A8'].load_liquid(liquid_objs["buffer"], volume=500)  # 500 ul 10x buffer
    tuberack['A9'].load_liquid(liquid_objs["enzyme"], volume=200)  # 200 ul enzyme
    
    # set temperature
    temp_mod.set_temperature(celsius=4)
    protocol.pause(msg="Reagents cooled to 4°C")
    
    # prepare reactions in plate wells A1-A12
    for i in range(12):
        well = plate.wells_by_name()[f"A{i+1}"]
        plasmid_well = tuberack[plasmid_well_names[i]]
        # water 12 ul
        p300.pick_up_tip()
        p300.aspirate(12, tuberack['A7'])  # water
        p300.dispense(12, well)
        p300.drop_tip()
        # buffer 2 ul
        p300.pick_up_tip()
        p300.aspirate(2, tuberack['A8'])
        p300.dispense(2, well)
        p300.drop_tip()
        # enzyme 1 ul
        p300.pick_up_tip()
        p300.aspirate(1, tuberack['A9'])
        p300.dispense(1, well)
        p300.drop_tip()
        # plasmid 5 ul
        p300.pick_up_tip()
        p300.aspirate(5, plasmid_well)
        p300.dispense(5, well)
        p300.drop_tip()
        # mix gently
        p300.pick_up_tip()
        p300.aspirate(10, well)
        p300.dispense(10, well)
        p300.drop_tip()
    
    temp_mod.deactivate()
