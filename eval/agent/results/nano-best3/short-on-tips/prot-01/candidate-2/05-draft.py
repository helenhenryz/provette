from opentrons import protocol_api

metadata = {"protocolName": "SDS-PAGE Sample Prep", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    dye = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#0000FF")
    samples = {}
    for i in range(1, 13):
        samples[f"sample {i}"] = protocol.define_liquid(name=f"sample {i}", description=f"Sample {i}", display_color="#000000")
    
    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    dye_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    tip_rack = protocol.load_labware("opentrons_96_tiprack_300ul", 3)
    
    # Load liquids into wells
    for i in range(1, 13):
        plate[f"A{i}"].load_liquid(liquid=samples[f"sample {i}"], volume=15)
    dye_plate["A1"].load_liquid(liquid=dye, volume=100)
    
    # Load pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tip_rack])
    
    # Transfer 5 µL dye into each sample well
    p300.pick_up_tip()
    for i in range(1, 13):
        p300.aspirate(5, dye_plate["A1"])
        p300.dispense(5, plate[f"A{i}"])
    p300.drop_tip()
