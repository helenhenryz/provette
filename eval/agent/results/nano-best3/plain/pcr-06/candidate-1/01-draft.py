from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR prep",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    pcr_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    pcr_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    colony_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    pcr_mix = protocol.define_liquid(name="pcr mix", description="PCR mix", display_color="#FF0000")
    pcr_reservoir["A1"].load_liquid(liquid=pcr_mix, volume=500)
    source_well_names = ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11","A12","B1","B2","B3","B4"]
    for i, well_name in enumerate(source_well_names, start=1):
        colony_liquid = protocol.define_liquid(name=f"colony {i}", description="Colony sample", display_color="#000000")
        colony_plate[well_name].load_liquid(liquid=colony_liquid, volume=100)

    # Perform transfers
    p300.pick_up_tip()
    for well_name in source_well_names:
        # Aspirate 20 ul of pcr mix
        p300.aspirate(20, pcr_reservoir["A1"])
        # Dispense into destination well
        p300.dispense(20, pcr_plate[well_name])
        # Aspirate 1 ul from colony source
        p300.aspirate(1, colony_plate[well_name])
        # Dispense into the same destination well
        p300.dispense(1, pcr_plate[well_name])
    p300.drop_tip()
