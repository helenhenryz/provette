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
    waste = pbs_res["A2"]  # waste well

    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack])

    transfer_vol = 50.0  # ul for each half of the dilution

    for i in range(12):
        well = plate["A" + str(i+1)]
        # transfer from source (stock or previous well)
        if i == 0:
            src = drug_tube["A1"]
        else:
            src = plate["A" + str(i)]
        p300.transfer(transfer_vol, src, well, new_tip='always')
        # add PBS diluent to reach 100 ul total
        p300.transfer(transfer_vol, pbs_res["A1"], well, new_tip='always')
        # mix
        p300.mix(5, 80, well)
        p300.blow_out()

    # no excess removal needed; each well ends at exactly 100 ul
