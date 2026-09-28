from opentrons import protocol_api

metadata = {"protocolName": "1:2 Serial Dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 1)
    tubes = protocol.load_labware("opentrons_15_tuberack_falcon_15ml_conical", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    pbs = protocol.define_liquid(name="pbs", description="PBS", display_color="#0000FF")
    drug = protocol.define_liquid(name="drug", description="Drug stock", display_color="#FF0000")

    # Load liquids into source wells
    reservoir["A1"].load_liquid(liquid=pbs, volume=1500)  # excess PBS
    tubes["A1"].load_liquid(liquid=drug, volume=100)     # enough drug

    # Pre-fill column A wells with 50 ul PBS each
    p300.pick_up_tip()
    for i in range(1, 13):
        p300.aspirate(50, reservoir["A1"])
        p300.dispense(50, plate[f"A{i}"])
    p300.drop_tip()

    # Add 50 ul drug to A1 with a fresh tip and mix
    p300.pick_up_tip()
    p300.aspirate(50, tubes["A1"])
    p300.dispense(50, plate["A1"])
    p300.mix(5, 50, plate["A1"])
    # Serial dilution transfers
    for i in range(2, 13):
        # Mix source well before drawing from it
        p300.mix(5, 50, plate[f"A{i-1}"])
        p300.aspirate(50, plate[f"A{i-1}"])
        p300.dispense(50, plate[f"A{i}"])
    # Add a blank well of PBS as negative control
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["H1"])
    p300.drop_tip()
