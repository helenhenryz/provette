import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "BSA Standard Curve", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 4)

    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    water_liq = protocol.define_liquid(
        name="water",
        description="distilled water",
        display_color="#FFFFFF"
    )
    bsa_liq = protocol.define_liquid(
        name="bsa",
        description="BSA stock 2 mg/ml",
        display_color="#FF0000"
    )

    # Load liquids onto deck
    tuberack["A1"].load_liquid(liquid=bsa_liq, volume=1000)  # BSA stock
    reservoir["A1"].load_liquid(liquid=water_liq, volume=1000)  # Water

    # Wells for standards (first 8 wells of plate, column-wise order)
    std_wells = plate.wells()[:8]  # A1, A2, A3, A4, A5, A6, A7, A8

    # Dilution series volumes from dilution_series tool
    # each element: (transfer_in_ul, add_diluent_ul, source_well)
    # We will transfer BSA (or previous dilution) first, then add water.
    # source_well: None for stock tuberack[A1]; otherwise previous std_well
    steps = [
        (100.0, 0.0, None),          # well 1: 100 ul BSA, 0 water
        (50.0, 50.0, std_wells[0]),  # well 2: 50 ul from well1, 50 water
        (50.0, 50.0, std_wells[1]),  # well 3: 50 ul from well2, 50 water
        (50.0, 50.0, std_wells[2]),  # well 4: 50 ul from well3, 50 water
        (50.0, 50.0, std_wells[3]),  # well 5: 50 ul from well4, 50 water
        (50.0, 50.0, std_wells[4]),  # well 6: 50 ul from well5, 50 water
        (50.0, 50.0, std_wells[5]),  # well 7: 50 ul from well6, 50 water
        (50.0, 50.0, std_wells[6])   # well 8: 50 ul from well7, 50 water
    ]

    # Perform dilution series
    for i, (transfer_vol, diluent_vol, src) in enumerate(steps):
        p300.pick_up_tip()
        # Transfer BSA (or previous dilution) first
        if src is None:
            src_loc = tuberack["A1"]
        else:
            src_loc = src
        p300.aspirate(transfer_vol, src_loc)
        p300.dispense(transfer_vol, std_wells[i])
        # Add water diluent
        if diluent_vol > 0:
            p300.aspirate(diluent_vol, reservoir["A1"])
            p300.dispense(diluent_vol, std_wells[i])
        # Mix: use larger volume to ensure good mixing
        p300.mix(5, 80, std_wells[i])
        p300.drop_tip()

    # Remove excess 50 ul from last well (well 8) to waste well reservoir[A2]
    p300.pick_up_tip()
    p300.aspirate(50.0, std_wells[7])
    p300.dispense(50.0, reservoir["A2"])
    p300.drop_tip()
