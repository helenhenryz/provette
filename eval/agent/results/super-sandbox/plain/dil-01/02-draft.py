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
    # waste well (use A2 of reservoir) - not needed now but keep
    waste = pbs_res["A2"]

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    # drug volumes per well from plate map (ul)
    drug_vols = [50.0, 25.0, 12.5, 6.25, 3.12, 1.56, 0.78, 0.39, 0.2, 0.1, 0.05, 0.02]

    for i, vol_drug in enumerate(drug_vols):
        well = plate["A" + str(i+1)]
        p300.pick_up_tip()
        # source for drug
        if i == 0:
            src = drug_tube["A1"]
        else:
            src = plate["A" + str(i)]  # previous well
        # transfer drug
        p300.aspirate(vol_drug, src)
        p300.dispense(vol_drug, well)
        # add PBS to reach 100 ul total
        vol_pbs = 100.0 - vol_drug
        p300.aspirate(vol_pbs, pbs_res["A1"])
        p300.dispense(vol_pbs, well)
        # mix
        p300.mix(3, 50, well)
        p300.drop_tip()

    # optional: remove excess from last well (not needed)
    # p300.pick_up_tip()
    # p300.aspirate(100, plate["A12"])
    # p300.dispense(100, waste)
    # p300.drop_tip()
