from opentrons import protocol_api

metadata = {"protocolName": "BSA Standard Curve", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "2")
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "3")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "4")
    
    # Define liquids
    protocol.define_liquid(name="water", description="water", display_color="#0000FF")
    protocol.define_liquid(name="bsa", description="BSA stock", display_color="#00FF00")
    
    # Load liquids into source wells
    tuberack["A1"].load_liquid(liquid="bsa", volume=200)
    reservoir["A1"].load_liquid(liquid="water", volume=5000)
    # Load waste tube with water (optional)
    tuberack["B1"].load_liquid(liquid="water", volume=1000)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Define dilution steps for 8 wells (A1-A8)
    dilution_steps = [
        {"diluent_vol": 0.0, "transfer_vol": 100.0, "source": tuberack["A1"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A1"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A2"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A3"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A4"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A5"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A6"]},
        {"diluent_vol": 50.0, "transfer_vol": 50.0, "source": plate["A7"]},
    ]
    
    # Process each step
    for i, step in enumerate(dilution_steps, start=1):
        target_well = plate[f"A{i}"]
        # Add diluent if needed
        if step["diluent_vol"] > 0:
            p300.pick_up_tip()
            p300.aspirate(step["diluent_vol"], reservoir["A1"])
            p300.dispense(step["diluent_vol"], target_well)
            p300.drop_tip()
        # Transfer in
        p300.pick_up_tip()
        p300.aspirate(step["transfer_vol"], step["source"])
        p300.dispense(step["transfer_vol"], target_well)
        # Mix
        p300.mix(10, 5, target_well)
        p300.drop_tip()
    
    # Remove 50 ul from the last well (A8) to waste
    p300.pick_up_tip()
    p300.aspirate(50, plate["A8"])
    p300.dispense(50, tuberack["B1"])
    p300.drop_tip()
