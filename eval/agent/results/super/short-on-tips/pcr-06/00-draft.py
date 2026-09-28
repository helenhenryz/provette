import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    pcr_mix_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    
    # liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR master mix", display_color="#FF0000")
    pcr_mix_tube["A1"].load_liquid(liquid=pcr_mix, volume=500)
    
    colony_liquids = []
    for i in range(1, 17):
        liq = protocol.define_liquid(name=f"colony {i}", description=f"Colony {i} suspension", display_color=None)
        colony_liquids.append(liq)
        colony_plate[f"{( (i-1)//8 )*2 + 65}{(i-1)%8 + 1}"].load_liquid(liquid=liq, volume=100)  # simple placement
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # distribute PCR mix (20 ul each) using same tip
    p20.pick_up_tip()
    for col in range(1, 17):
        well = pcr_plate[f"{chr(64+col)}1"] if col <= 8 else pcr_plate[f"{chr(64+(col-8))}2"]
        p20.aspirate(20, pcr_mix_tube["A1"])
        p20.dispense(20, well)
    p20.drop_tip()
    
    # add 1 ul colony to each well, new tip each
    for i in range(1, 17):
        p20.pick_up_tip()
        src_well = colony_plate[f"{( (i-1)//8 )*2 + 65}{(i-1)%8 + 1}"]
        dest_well = pcr_plate[f"{chr(64+i)}1"] if i <= 8 else pcr_plate[f"{chr(64+(i-8))}2"]
        p20.aspirate(1, src_well)
        p20.dispense(1, dest_well)
        p20.drop_tip()
