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
        if i <= 12:
            well = f"A{i}"
        else:
            well = f"B{i-12}"
        colony_plate[well].load_liquid(liquid=liq, volume=100)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # distribute PCR mix (20 ul each) using same tip
    p20.pick_up_tip()
    for i in range(1, 17):
        # destination wells: first row A columns 1-12 then B columns 1-4
        if i <= 12:
            dest = f"A{i}"
        else:
            dest = f"B{i-12}"
        p20.aspirate(20, pcr_mix_tube["A1"])
        p20.dispense(20, pcr_plate[dest])
    p20.drop_tip()
    
    # add 1 ul colony to each well, new tip each
    for i in range(1, 17):
        p20.pick_up_tip()
        if i <= 12:
            src = f"A{i}"
            dest = f"A{i}"
        else:
            src = f"B{i-12}"
            dest = f"B{i-12}"
        p20.aspirate(1, colony_plate[src])
        p20.dispense(1, pcr_plate[dest])
        p20.drop_tip()
