from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)

    # Define liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR mix", display_color="#0000FF")
    
    # Load colony liquids into the first 16 wells of colony_plate (column-major order)
    colony_well_names = [str(well) for well in colony_plate.wells()[:16]]
    for i, well_name in enumerate(colony_well_names, start=1):
        col_liq = protocol.define_liquid(name=f"colony {i}", description=f"Colony {i} resuspension", display_color="#000000")
        colony_plate.well(well_name).load_liquid(liquid=col_liq, volume=100)

    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=pcr_mix, volume=500)

    # Load pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack_20])

    # Transfer 20 µL of pcr mix into each of the 16 destination wells
    pcr_mix_source = reservoir["A1"]
    p20.pick_up_tip()
    for well in plate.wells()[:16]:
        p20.aspirate(20, pcr_mix_source)
        p20.dispense(20, well)
    p20.drop_tip()

    # Add 1 µL from each colony resuspension to the corresponding well, mixing after each
    for i, well in enumerate(plate.wells()[:16]):
        colony_well = colony_plate.wells()[i]
        p20.pick_up_tip()
        p20.aspirate(1, colony_well)
        p20.dispense(1, well)
        # Mix 5 times with ~80% of well volume (approx 17 µL)
        p20.mix(5, 17, well)
        p20.drop_tip()
