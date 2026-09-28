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
    p300_multi = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tip_rack])
    
    # Aspirate dye and dispense into sample wells
    p300_multi.pick_up_tip()
    p300_multi.aspirate(5, dye_plate["A1"])
    # dispense into first 8 wells
    p300_multi.dispense(5, [plate["A1"], plate["A2"], plate["A3"], plate["A4"], plate["A7"], plate["A6"], plate["A5"], plate["A4"]])
    # dispense into remaining 4 wells
    p300_multi.dispense(5, [plate["A9"], plate["A10"], plate["A11"], plate["A12"]])
    p300_multi.drop_tip()
