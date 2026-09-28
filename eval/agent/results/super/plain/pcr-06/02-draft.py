import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    pcr_tube_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack])
    
    # liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR master mix", display_color="#FF0000")
    colony_liquids = []
    for i in range(1, 17):
        liq = protocol.define_liquid(name=f"colony {i}", description=f"Colony {i} suspension", display_color="#00FF00")
        colony_liquids.append(liq)
    
    # assign initial volumes
    pcr_tube_rack["A1"].load_liquid(liquid=pcr_mix, volume=500)  # excess
    for i in range(16):
        # place colony suspensions in same order as destinations (column-wise)
        col = chr(65 + (i // 8))  # A for first 8, B for next 8
        row = (i % 8) + 1
        colony_plate[f"{col}{row}"].load_liquid(liquid=colony_liquids[i], volume=200)
    
    # destination wells: first two columns (A1-A8, B1-B8) column-wise
    dest_wells = []
    for col in ["A", "B"]:
        for row in range(1, 9):
            dest_wells.append(f"{col}{row}")
    
    # distribute PCR mix then add colony, then mix
    for idx, well in enumerate(dest_wells):
        # add PCR mix
        p20.pick_up_tip()
        p20.aspirate(20, pcr_tube_rack["A1"])
        p20.dispense(20, pcr_plate[well])
        p20.drop_tip()
        # add colony
        p20.pick_up_tip()
        colony_source = colony_plate.wells()[idx]
        p20.aspirate(1, colony_source)
        p20.dispense(1, pcr_plate[well])
        # mix after addition
        p20.mix(5, 20, pcr_plate[well])
        p20.drop_tip()
