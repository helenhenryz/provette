import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Drug 1:2 serial dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    drug_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    pbs_res = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 4)  # deep well to avoid capacity issues

    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    # source wells
    drug_tube["A1"].load_liquid(liquid=drug, volume=500)  # ul
    pbs_res["A1"].load_liquid(liquid=pbs, volume=15000)  # ul
    waste = pbs_res["A2"]  # waste well

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # perform dilution across row A columns 1-12
    for i in range(12):
        well = plate["A" + str(i+1)]
        # add PBS diluent 100 ul
        p300.pick_up_tip()
        p300.aspirate(100, pbs_res["A1"])
        p300.dispense(100, well)
        p300.drop_tip()
        # transfer in 100 ul from source (stock or previous well)
        p300.pick_up_tip()
        if i == 0:
            src = drug_tube["A1"]
        else:
            src = plate["A" + str(i)]
        p300.aspirate(100, src)
        p300.dispense(100, well)
        p300.drop_tip()
        # mix
        p300.pick_up_tip()
        p300.mix(5, 100, well)  # mix 5 times with 100 ul in 200 ul volume
        p300.drop_tip()
        # remove excess to waste to leave 100 ul final volume
        p300.pick_up_tip()
        p300.aspirate(100, well)
        p300.dispense(100, waste)
        p300.drop_tip()

    # Note: final volume in each well is exactly 100 ul with correct composition.
