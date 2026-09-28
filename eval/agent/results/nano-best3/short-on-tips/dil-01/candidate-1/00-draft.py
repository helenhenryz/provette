from opentrons import protocol_api

metadata = {
    "protocolName": "Serial Dilution Drug",
    "apiLevel": "2.19"
}


def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    pbs_reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)

    # Define liquids
    pbs = protocol.define_liquid(name="pbs", description="PBS", display_color="#0000FF")
    drug = protocol.define_liquid(name="drug", description="Drug stock", display_color="#FF0000")

    # Load liquids onto deck
    tubes["A1"].load_liquid(liquid=drug, volume=1000)  # load drug stock
    pbs_reservoir["A1"].load_liquid(liquid=pbs, volume=2000)  # load PBS

    # Load tip
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300.pick_up_tip()

    # Prefill plate wells with 50 ul PBS
    for i in range(1, 13):
        well = plate[f"A{i}"]
        p300.aspirate(50, pbs_reservoir["A1"])
        p300.dispense(50, well)

    # Transfer 50 ul drug into A1
    p300.aspirate(50, tubes["A1"])
    p300.dispense(50, plate["A1"])

    # Serial transfers from A1 to A12
    for i in range(2, 13):
        source = plate[f"A{i-1}"]
        dest = plate[f"A{i}"]
        p300.aspirate(50, source)
        p300.dispense(50, dest)

    p300.drop_tip()
