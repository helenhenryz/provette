from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    colony_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)

    # Pipette
    p300_multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tip_rack])

    # Define liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR mix", display_color="#FF0000")
    colony_liquids = {}
    for i in range(1, 17):
        colony_name = f"colony {i}"
        colony_liquids[i] = protocol.define_liquid(name=colony_name, description=f"Colony {i} resuspension", display_color="#000000")

    # Load liquids
    reservoir["A1"].load_liquid(liquid=pcr_mix, volume=2000)
    for i, well_name in enumerate(["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4"], start=1):
        colony_plate[well_name].load_liquid(liquid=colony_liquids[i], volume=100)

    # Destination and source well lists for two batches of 8
    batch1_dest_wells = [dest_plate["A1"], dest_plate["A2"], dest_plate["A3"], dest_plate["A4"],
                         dest_plate["A5"], dest_plate["A6"], dest_plate["A7"], dest_plate["A8"]]
    batch1_source_wells = [colony_plate["A1"], colony_plate["A2"], colony_plate["A3"], colony_plate["A4"],
                           colony_plate["A5"], colony_plate["A6"], colony_plate["A7"], colony_plate["A8"]]
    batch2_dest_wells = [dest_plate["A9"], dest_plate["A10"], dest_plate["A11"], dest_plate["A12"],
                         dest_plate["B1"], dest_plate["B2"], dest_plate["B3"], dest_plate["B4"]]
    batch2_source_wells = [colony_plate["A9"], colony_plate["A10"], colony_plate["A11"], colony_plate["A12"],
                           colony_plate["B1"], colony_plate["B2"], colony_plate["B3"], colony_plate["B4"]]

    # Batch 1
    p300_multi.pick_up_tip()
    for i in range(len(batch1_dest_wells)):
        p300_multi.aspirate(20, reservoir["A1"])
        p300_multi.dispense(20, batch1_dest_wells[i])
        p300_multi.aspirate(1, batch1_source_wells[i])
        p300_multi.dispense(1, batch1_dest_wells[i])
    p300_multi.drop_tip()

    # Batch 2
    p300_multi.pick_up_tip()
    for i in range(len(batch2_dest_wells)):
        p300_multi.aspirate(20, reservoir["A1"])
        p300_multi.dispense(20, batch2_dest_wells[i])
        p300_multi.aspirate(1, batch2_source_wells[i])
        p300_multi.dispense(1, batch2_dest_wells[i])
    p300_multi.drop_tip()
