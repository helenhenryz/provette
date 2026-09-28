from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_filtertiprack_200ul", 1)
    p20_tips = protocol.load_labware("opentrons_96_tiprack_10ul", 5)
    pcr_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    colonies_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Define liquids
    pcr_mix_liquid = protocol.define_liquid(name="pcr mix", description="PCR master mix", display_color="#1f77b4")
    colony_liquids = []
    for i in range(1, 17):
        colony_liquid = protocol.define_liquid(name=f"colony {i}", description=f"Colony {i}", display_color=f"#{i*5:06x}")
        colony_liquids.append(colony_liquid)

    # Load liquids
    reservoir["A1"].load_liquid(liquid=pcr_mix_liquid, volume=500)
    for i in range(1, 17):
        colony_well = colonies_plate.wells()[i-1]
        colony_well.load_liquid(liquid=colony_liquids[i-1], volume=50)

    # Load instruments
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[p20_tips])

    # Transfers
    for i in range(16):
        # Add 20 ul pcr mix
        p300.pick_up_tip()
        p300.aspirate(20, reservoir["A1"])
        dest_well = pcr_plate.wells()[i]
        p300.dispense(20, dest_well)
        p300.drop_tip()
        
        # Add 1 ul colony
        p20.pick_up_tip()
        colony_well = colonies_plate.wells()[i]
        p20.aspirate(1, colony_well)
        p20.dispense(1, dest_well)
        p20.drop_tip()
