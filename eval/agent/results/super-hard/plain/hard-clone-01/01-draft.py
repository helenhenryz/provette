import json
from opentrons import protocol_api

metadata = {"protocolName": "24 ligation reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    insert_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # define liquids
    buffer = protocol.define_liquid(name="buffer", description="10x T4 DNA ligase buffer", display_color="#0000FF")
    ligase = protocol.define_liquid(name="ligase", description="T4 DNA ligase", display_color="#FF0000")
    vector = protocol.define_liquid(name="vector", description="cut vector", display_color="#00FF00")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    for i in range(1, 25):
        protocol.define_liquid(name=f"insert {i}", description=f"insert {i}", display_color="#FFA500")
    
    # load liquids into sources
    tuberack["A1"].load_liquid(liquid=buffer, volume=100)   # buffer
    tuberack["A2"].load_liquid(liquid=ligase, volume=50)    # ligase
    tuberack["A3"].load_liquid(liquid=vector, volume=100)   # vector
    tuberack["A4"].load_liquid(liquid=water, volume=300)    # water
    
    for i in range(1, 25):
        well = f"{chr(ord('A') + (i-1)%8)}{((i-1)//8)+1}"
        insert_plate[well].load_liquid(liquid=protocol.define_liquid(name=f"insert {i}", description=f"insert {i}", display_color="#FFA500"), volume=100)
    
    # helper to aspirate volume in chunks <=20 ul
    def chunk_aspirate(pipette, volume, source):
        while volume > 0:
            chunk = min(20, volume)
            pipette.aspirate(chunk, source)
            volume -= chunk
    
    # helper to dispense volume in chunks <=20 ul
    def chunk_dispense(pipette, volume, dest):
        while volume > 0:
            chunk = min(20, volume)
            pipette.dispense(chunk, dest)
            volume -= chunk
    
    # pool master mix (buffer+ligase+vector+water) with 10% overage
    vol_buffer = 2 * 24 * 1.1  # 52.8
    vol_ligase = 1 * 24 * 1.1  # 26.4
    vol_vector = 3 * 24 * 1.1  # 79.2
    vol_water  = 9 * 24 * 1.1  # 237.6
    
    mix_tube = tuberack["A5"]
    p20.pick_up_tip()
    # buffer
    chunk_aspirate(p20, vol_buffer, tuberack["A1"])
    # ligase
    chunk_aspirate(p20, vol_ligase, tuberack["A2"])
    # vector
    chunk_aspirate(p20, vol_vector, tuberack["A3"])
    # water
    chunk_aspirate(p20, vol_water, tuberack["A4"])
    # dispense all into mix tube
    chunk_dispense(p20, vol_buffer+vol_ligase+vol_vector+vol_water, mix_tube)
    p20.mix(5, 20, mix_tube)  # mix with 20 ul chunks
    p20.drop_tip()
    
    # dispense 15 ul of master mix into each destination well (24 wells)
    dest_wells = []
    for col in range(1, 13):
        for row in range(8):
            if len(dest_wells) >= 24:
                break
            dest_wells.append(f"{chr(ord('A')+row)}{col}")
        if len(dest_wells) >= 24:
            break
    
    p20.pick_up_tip()
    for well in dest_wells:
        p20.aspirate(15, mix_tube)
        p20.dispense(15, dest_plate[well])
        p20.mix(2, 15, dest_plate[well])
    p20.drop_tip()
    
    # add 5 ul of each insert to corresponding dest well
    for i in range(1, 25):
        insert_well = f"{chr(ord('A') + (i-1)%8)}{((i-1)//8)+1}"
        dest_well = dest_wells[i-1]
        p20.pick_up_tip()
        p20.aspirate(5, insert_plate[insert_well])
        p20.dispense(5, dest_plate[dest_well])
        p20.mix(2, 5, dest_plate[dest_well])
        p20.drop_tip()
