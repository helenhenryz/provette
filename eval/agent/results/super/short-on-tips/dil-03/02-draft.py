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
    # each element: (add_diluent_ul, transfer_in_ul, source_well)
    # source_well: None for stock tuberack[A1]; otherwise previous std_well
    vols = [
        (0.0, 100.0, None),          # well 1
        (50.0, 50.0, std_wells[0]),  # well 2 from well1
        (50.0, 50.0, std_wells[1]),  # well 3 from well2
        (50.0, 50.0, std_wells[2]),  # well 4 from well3
        (50.0, 50.0, std_wells[3]),  # well 5 from well4
        (50.0, 50.0, std_wells[4]),  # well 6 from well5
        (50.0, 50.0, std_wells[5]),  # well 7 from well6
        (50.0, 50.0, std_wells[6])   # well 8 from well7
    ]

    # Perform dilution series
    for i, (diluent_vol, transfer_vol, src) in enumerate(vols):
        p300.pick_up_tip()
        if diluent_vol > 0:
            p300.aspirate(diluent_vol, reservoir["A1"])
            p300.dispense(diluent_vol, std_wells[i])
        # Transfer BSA (or previous dilution)
        if src is None:
            src_loc = tuberack["A1"]
        else:
            src_loc = src
        p300.aspirate(transfer_vol, src_loc)
        p300.dispense(transfer_vol, std_wells[i])
        # Mix
        p300.mix(3, 25, std_wells[i])
        p300.drop_tip()

    # Remove excess 50 ul from last well (well 8) to waste well reservoir[A2]
    p300.pick_up_tip()
    p300.aspirate(50.0, std_wells[7])
    p300.dispense(50.0, reservoir["A2"])
    p300.drop_tip()
