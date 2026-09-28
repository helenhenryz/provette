from opentrons import protocol_api

metadata = {"protocolName": "Serial Dilution of Drug into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_filtertiprack_200ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    drug = protocol.define_liquid(name="drug", description="Drug stock", display_color="#FF0000")
    pbs = protocol.define_liquid(name="pbs", description="PBS", display_color="#0000FF")

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=drug, volume=150)
    reservoir["A1"].load_liquid(liquid=pbs, volume=1500)

    # Define the series of wells (column A, rows 1-12)
    wells = [f"A{i+1}" for i in range(12)]

    # Perform serial dilution
    for i, well_name in enumerate(wells):
        # Pick up a tip
        p300.pick_up_tip()
        # Add 100 ul of PBS (diluent) to the well
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, plate[well_name])
        # Transfer 100 ul from source (stock for first well, previous well thereafter)
        if i == 0:
            source = tubes["A1"]
        else:
            source = plate[wells[i-1]]
        p300.aspirate(100, source)
        p300.dispense(100, plate[well_name])
        # Mix the well
        p300.mix(20, well_name, 5)
        # If this is the last well, aspirate 100 ul to waste
        if i == 11:
            p300.aspirate(100, plate[well_name])
        # Drop tip
        p300.drop_tip()
