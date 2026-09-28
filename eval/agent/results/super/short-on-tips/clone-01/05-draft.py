import json
from opentrons import protocol_api

metadata = {"protocolName": "Restriction Digest Setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # temperature module
    temp_mod = protocol.load_module("temperature module gen2", "1")
    # aluminum block on temp block holding 1.5ml tubes
    tuberack = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    # tip rack for p20
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", "2")
    # destination PCR plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "3")
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
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
    # reagents in C1-C3
    tuberack['C1'].load_liquid(liquid_objs["water"], volume=1000)   # 1 ml water
    tuberack['C2'].load_liquid(liquid_objs["buffer"], volume=500)  # 500 ul 10x buffer
    tuberack['C3'].load_liquid(liquid_objs["enzyme"], volume=200)  # 200 ul enzyme
    
    # set temperature
    temp_mod.set_temperature(celsius=4)
    protocol.pause(msg="Reagents cooled to 4°C")
    
    # prepare reactions in plate wells A1-A12
    for i in range(12):
        well = plate.wells_by_name()[f"A{i+1}"]
        plasmid_well = tuberack[plasmid_well_names[i]]
        # water 12 ul
        p20.pick_up_tip()
        p20.aspirate(12, tuberack['C1'])  # water
        p20.dispense(12, well)
        p20.drop_tip()
        # buffer 2 ul
        p20.pick_up_tip()
        p20.aspirate(2, tuberack['C2'])
        p20.dispense(2, well)
        p20.drop_tip()
        # enzyme 1 ul
        p20.pick_up_tip()
        p20.aspirate(1, tuberack['C3'])
        p20.dispense(1, well)
        p20.drop_tip()
        # plasmid 5 ul and mix
        p20.pick_up_tip()
        p20.aspirate(5, plasmid_well)
        p20.dispense(5, well)
        # mix 5 times 16 ul (80% of 20 ul)
        p20.mix(5, 16, well)
        p20.drop_tip()
    
    temp_mod.deactivate()
