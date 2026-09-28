from opentrons import protocol_api

metadata = {"protocolName": "BSA Standard Curve", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tip_racks = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", "2")
    water_reservoir = protocol.load_labware("nest_12_reservoir_15ml", "3")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "4")
    waste_reservoir = protocol.load_labware("nest_12_reservoir_15ml", "5")

    # Define liquids
    bsa_liquid = protocol.define_liquid(name="bsa", description=None, display_color='#1f77b4')
    water_liquid = protocol.define_liquid(name="water", description=None, display_color='#ff7f0e')

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=bsa_liquid, volume=1000)
    water_reservoir["A1"].load_liquid(liquid=water_liquid, volume=1000)

    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_racks])

    # Define wells for the standard curve
    wells = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"]

    # Perform serial dilution
    for i, well in enumerate(wells, start=1):
        if i == 1:
            add_diluent_vol = 0.0
            transfer_vol = 100.0
            source = tubes["A1"]  # stock BSA
        else:
            add_diluent_vol = 50.0
            transfer_vol = 50.0
            source = plate[wells[i-2]]  # previous well

        # Add diluent (water)
        if add_diluent_vol > 0:
            p300.aspirate(add_diluent_vol, water_reservoir["A1"])
            p300.dispense(add_diluent_vol, plate[well])

        # Transfer in from source
        p300.aspirate(transfer_vol, source)
        p300.dispense(transfer_vol, plate[well])

        # Mix
        p300.mix(volume=transfer_vol + add_diluent_vol, repeats=3)

    # Remove excess from the last well
    p300.aspirate(50, plate["A8"])
    p300.dispense(50, waste_reservoir["A1"])

    # Drop tip
    p300.drop_tip()
