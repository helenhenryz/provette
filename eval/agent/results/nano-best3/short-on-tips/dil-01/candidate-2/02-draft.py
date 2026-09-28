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
    reservoir["A1"].load_liquid(liquid=pbs, volume=2000)  # enough PBS
    tubes["A1"].load_liquid(liquid=drug, volume=100)     # enough drug

    # Define drug volumes for each well (1:2 dilution series)
    drug_volumes = [50, 25, 12.5, 6.25, 3.125, 1.5625, 0.78125, 0.390625, 0.1953125, 0.09765625, 0.048828125, 0.0244140625]

    # Pre-fill each well with appropriate PBS volume and add drug
    for i in range(1, 13):
        # Add PBS to reach 100 ul total volume
        pbs_vol = 100 - drug_volumes[i-1]
        p300.pick_up_tip()
        p300.aspirate(pbs_vol, reservoir["A1"])
        p300.dispense(pbs_vol, plate[f"A{i}"])
        # Add drug
        p300.aspirate(drug_volumes[i-1], tubes["A1"])
        p300.dispense(drug_volumes[i-1], plate[f"A{i}"])
        # Mix after addition
        p300.mix(5, drug_volumes[i-1] + pbs_vol, plate[f"A{i}"])
        p300.drop_tip()
    
    # Add a blank well of PBS alone as negative control
    p300.pick_up_tip()
    p300.aspirate(100, reservoir["A1"])
    p300.dispense(100, plate["H1"])
    p300.drop_tip()
