from opentrons import protocol_api

metadata = {"protocolName": "Colony PCR prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 1)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    tiprack_1000 = protocol.load_labware("opentrons_96_tiprack_1000ul", 4)
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)

    # Define liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR mix", display_color="#0000FF")
    colony_liquids = []
    colony_well_names = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4"]
    for i, well_name in enumerate(colony_well_names, start=1):
        col_liq = protocol.define_liquid(name=f"colony {i}", description=f"Colony {i} resuspension", display_color="#000000")
        colony_liquids.append(col_liq)
        colony_plate[well_name].load_liquid(liquid=col_liq, volume=100)

    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=pcr_mix, volume=500)

    # Load pipettes
    p1000 = protocol.load_instrument("p1000_single_gen2", "right", tip_racks=[tiprack_1000])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack_20])

    # Transfer 20 µL of pcr mix into each of the 16 destination wells
    pcr_mix_source = reservoir["A1"]
    p1000.pick_up_tip()
    for well in plate.wells()[:16]:
        p1000.aspirate(20, pcr_mix_source)
        p1000.dispense(20, well)
    p1000.drop_tip()

    # Add 1 µL from each colony resuspension to the corresponding well
    for i, well in enumerate(plate.wells()[:16]):
        colony_well = colony_plate.wells()[i]
        p20.pick_up_tip()
        p20.aspirate(1, colony_well)
        p20.dispense(1, well)
        p20.drop_tip()
