import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    pcr_mix_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    water_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)
    
    # liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR master mix", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    pcr_mix_tube["A1"].load_liquid(liquid=pcr_mix, volume=500)
    water_tube["A1"].load_liquid(liquid=water, volume=500)
    
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
        if i <= 12:
            dest = f"A{i}"
        else:
            dest = f"B{i-12}"
        p20.aspirate(20, pcr_mix_tube["A1"])
        p20.dispense(20, pcr_plate[dest])
    p20.drop_tip()
    
    # add samples or water (NTC) to each well, new tip each, mix after
    for i in range(1, 17):
        p20.pick_up_tip()
        if i == 12:  # make well L? actually column 12 row B? Let's decide NTC at column 12 row B (i=12 corresponds to B12? Wait mapping)
            # we designated NTC at well column 12 row B? easier: make well H12? let's just use column 12 row B as NTC (i=12 => B12)
            src = water_tube["A1"]
            dest_well = pcr_plate[f"B12"]
        else:
            if i <= 12:
                src = colony_plate[f"A{i}"]
                dest_well = pcr_plate[f"A{i}"]
            else:
                src = colony_plate[f"B{i-12}"]
                dest_well = pcr_plate[f"B{i-12}"]
        p20.aspirate(1, src)
        p20.dispense(1, dest_well)
        p20.mix(5, 16, dest_well)  # mix 5 times 16ul
        p20.drop_tip()
