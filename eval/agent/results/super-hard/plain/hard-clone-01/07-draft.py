from opentrons import protocol_api

metadata = {"protocolName": "24 ligation reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)  # for mixing
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    insert_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    dest_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    
    # define liquids with hints about type
    buffer = protocol.define_liquid(name="buffer", description="assay buffer diluent", display_color="#0000FF")
    ligase = protocol.define_liquid(name="ligase", description="T4 DNA ligase enzyme", display_color="#FF0000")
    vector = protocol.define_liquid(name="vector", description="cut vector sample", display_color="#00FF00")
    water = protocol.define_liquid(name="water", description="nuclease-free water diluent", display_color="#FFFFFF")
    for i in range(1, 25):
        protocol.define_liquid(name=f"insert {i}", description=f"insert {i} sample", display_color="#FFA500")
    
    # load liquids into sources
    tuberack["A1"].load_liquid(liquid=buffer, volume=100)   # buffer
    tuberack["A2"].load_liquid(liquid=ligase, volume=50)    # ligase
    tuberack["A3"].load_liquid(liquid=vector, volume=100)   # vector
    tuberack["A4"].load_liquid(liquid=water, volume=300)    # water
    
    for i in range(1, 25):
        well = f"{chr(ord('A') + (i-1)%8)}{((i-1)//8)+1}"
        insert_plate[well].load_liquid(liquid=protocol.define_liquid(name=f"insert {i}", description=f"insert {i} sample", display_color="#FFA500"), volume=100)
    
    # pool master mix (buffer+ligase+vector+water) with 10% overage
    # order: water, buffer, vector, ligase (enzyme last)
    vol_water  = 9 * 24 * 1.1  # 237.6
    vol_buffer = 2 * 24 * 1.1  # 52.8
    vol_vector = 3 * 24 * 1.1  # 79.2
    vol_ligase = 1 * 24 * 1.1  # 26.4
    
    mix_tube = tuberack["A5"]
    # water first (needs p300 as >20 ul)
    p300.transfer(vol_water, tuberack["A4"], mix_tube, new_tip='always')
    # then buffer, vector, ligase with p20
    p20.transfer(vol_buffer, tuberack["A1"], mix_tube, new_tip='always')
    p20.transfer(vol_vector, tuberack["A3"], mix_tube, new_tip='always')
    p20.transfer(vol_ligase, tuberack["A2"], mix_tube, new_tip='always')
    # mix the combined master mix with p300 (large enough)
    p300.pick_up_tip()
    p300.mix(5, 200, mix_tube)  # 200ul <300, ok
    p300.drop_tip()
    
    # dispense 15 ul of master mix into each destination well (24 wells)
    dest_wells = []
    for col in range(1, 13):
        for row in range(8):
            if len(dest_wells) >= 24:
                break
            dest_wells.append(f"{chr(ord('A')+row)}{col}")
        if len(dest_wells) >= 24:
            break
    
    for well in dest_wells:
        p20.transfer(15, mix_tube, dest_plate[well], new_tip='always', mix_after=(5, 12))  # 80% of 15 =12
    
    # add 5 ul of each insert to corresponding dest well
    for i in range(1, 25):
        insert_well = f"{chr(ord('A') + (i-1)%8)}{((i-1)//8)+1}"
        dest_well = dest_wells[i-1]
        p20.transfer(5, insert_plate[insert_well], dest_plate[dest_well], new_tip='always', mix_after=(5, 16))  # 80% of 20 =16
