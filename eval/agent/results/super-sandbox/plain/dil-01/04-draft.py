import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Drug 1:2 serial dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    drug_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    pbs_res = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    # source wells
    drug_tube["A1"].load_liquid(liquid=drug, volume=500)  # ul
    pbs_res["A1"].load_liquid(liquid=pbs, volume=15000)  # ul
    waste = pbs_res["A2"]  # waste well (unused but defined)

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    transfer_vol = 50.0  # ul, for 1:2 dilution into 100 ul final volume

    for i in range(12):
        well = plate["A" + str(i+1)]
        p300.pick_up_tip()
        if i == 0:
            # first well: get drug from stock
            src = drug_tube["A1"]
        else:
            # subsequent wells: get from previous well
            src = plate["A" + str(i)]
        p300.aspirate(transfer_vol, src)
        p300.dispense(transfer_vol, well)
        # add PBS diluent
        p300.aspirate(transfer_vol, pbs_res["A1"])
        p300.dispense(transfer_vol, well)
        # mix
        p300.mix(3, 40, well)  # mix 3 times with 40 ul (less than total volume)
        p300.drop_tip()

    # remove excess from last well (not needed as volume is exactly 100)
    # p300.pick_up_tip()
    # p300.aspirate(transfer_vol, plate["A12"])
    # p300.dispense(transfer_vol, waste)
    # p300.drop_tip()
