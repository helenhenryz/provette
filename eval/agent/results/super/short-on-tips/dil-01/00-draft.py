import json
from opentrons import protocol_api

metadata = {"protocolName": "1:2 serial dilution drug into PBS", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # pipette
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # define liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    
    # load liquids into sources
    tuberack["A1"].load_liquid(liquid=drug, volume=500)  # drug stock
    reservoir["A1"].load_liquid(liquid=pbs, volume=15000)  # PBS
    
    # volumes per well from platemap
    drug_vols = [50.0, 25.0, 12.5, 6.25, 3.12, 1.56, 0.78, 0.39, 0.2, 0.1, 0.05, 0.02]
    pbs_vols = [100 - v for v in drug_vols]
    
    # wells A1 to A12
    well_names = [f"A{i+1}" for i in range(12)]
    
    for i, well in enumerate(well_names):
        p20.pick_up_tip()
        # source for drug: stock for first well, previous well thereafter
        if i == 0:
            drug_source = tuberack["A1"]
        else:
            drug_source = plate[well_names[i-1]]
        p20.aspirate(drug_vols[i], drug_source)
        p20.dispense(drug_vols[i], plate[well])
        # add PBS
        p20.aspirate(pbs_vols[i], reservoir["A1"])
        p20.dispense(pbs_vols[i], plate[well])
        # mix
        p20.mix(2, 50, plate[well])
        p20.drop_tip()
    
