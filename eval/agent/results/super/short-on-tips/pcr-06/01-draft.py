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
        # place each colony in column i, row A of colony plate
        colony_plate[f"A{i}"].load_liquid(liquid=liq, volume=100)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # distribute PCR mix (20 ul each) using same tip
    p20.pick_up_tip()
    for i in range(1, 17):
        dest_well = pcr_plate[f"B{i}"]  # row B columns 1-16
        p20.aspirate(20, pcr_mix_tube["A1"])
        p20.dispense(20, dest_well)
    p20.drop_tip()
    
    # add 1 ul colony to each well, new tip each
    for i in range(1, 17):
        p20.pick_up_tip()
        src_well = colony_plate[f"A{i}"]
        dest_well = pcr_plate[f"B{i}"]
        p20.aspirate(1, src_well)
        p20.dispense(1, dest_well)
        p20.drop_tip()
