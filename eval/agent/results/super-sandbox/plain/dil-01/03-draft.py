import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "Drug 1:2 serial dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tiprack20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tiprack300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    drug_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    pbs_res = protocol.load_labware("nest_12_reservoir_15ml", 4)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)

    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    # source wells
    drug_tube["A1"].load_liquid(liquid=drug, volume=500)  # ul
    pbs_res["A1"].load_liquid(liquid=pbs, volume=15000)  # ul
    waste = pbs_res["A2"]  # waste well

    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack20])
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack300])

    # drug volumes per well from plate map (ul)
    drug_vols = [50.0, 25.0, 12.5, 6.25, 3.12, 1.56, 0.78, 0.39, 0.2, 0.1, 0.05, 0.02]

    for i, vol_drug in enumerate(drug_vols):
        well = plate["A" + str(i+1)]
        vol_pbs = 100.0 - vol_drug

        # add PBS first (large volume) with p300
        p300.pick_up_tip()
        p300.aspirate(vol_pbs, pbs_res["A1"])
        p300.dispense(vol_pbs, well)
        p300.drop_tip()

        # add drug with appropriate pipette
        if vol_drug > 20:
            pip = p300
            tiprack = tiprack300
        else:
            pip = p20
            tiprack = tiprack20
        pip.pick_up_tip()
        # source: stock for first well, previous well after
        if i == 0:
            src = drug_tube["A1"]
        else:
            src = plate["A" + str(i)]
        pip.aspirate(vol_drug, src)
        pip.dispense(vol_drug, well)
        pip.drop_tip()

        # mix well with p300 (volume 100 ul)
        p300.pick_up_tip()
        p300.mix(5, 80, well)
        p300.drop_tip()

    # remove excess from last well (optional, not needed as volume is exactly 100)
    # p300.pick_up_tip()
    # p300.aspirate(100, plate["A12"])
    # p300.dispense(100, waste)
    # p300.drop_tip()
