# A 1:2 serial dilution of a drug across one row, written by a model with the checks as its
# tools; the replay tests (web/src/replay, web/src/lib/plate.test.ts) draw its export,
# `analysis-dil-series.json` (make web-fixtures).
import opentrons
from opentrons import protocol_api

metadata = {"protocolName": "1:2 drug dilution", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    drug_tube = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 4)
    
    # liquids
    pbs = protocol.define_liquid(name="pbs", description="phosphate buffered saline", display_color="#00FF00")
    drug = protocol.define_liquid(name="drug", description="drug stock", display_color="#FF0000")
    waste = protocol.define_liquid(name="waste", description="waste", display_color="#FFFFFF")
    
    # load liquids
    drug_tube["A1"].load_liquid(liquid=drug, volume=500)  # excess
    reservoir["A1"].load_liquid(liquid=pbs, volume=2000)   # excess
    reservoir["A2"].load_liquid(liquid=waste, volume=0)
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    def well(col):
        return f"A{col}"
    
    # Well 1: neat drug
    p300.pick_up_tip()
    p300.aspirate(200, drug_tube["A1"])
    p300.dispense(200, plate[well(1)])
    p300.mix(3, 150, plate[well(1)])
    p300.drop_tip()
    
    # Wells 2-12
    for i in range(2, 13):
        dest = plate[well(i)]
        src = plate[well(i-1)]
        # Add PBS
        p300.pick_up_tip()
        p300.aspirate(100, reservoir["A1"])
        p300.dispense(100, dest)
        p300.drop_tip()
        # Transfer from previous well
        p300.pick_up_tip()
        p300.aspirate(100, src)
        p300.dispense(100, dest)
        p300.mix(3, 150, dest)
        p300.drop_tip()
    
    # Remove excess from last well (well 12) 100 ul to waste
    p300.pick_up_tip()
    p300.aspirate(100, plate[well(12)])
    p300.dispense(100, reservoir["A2"])
    p300.drop_tip()
