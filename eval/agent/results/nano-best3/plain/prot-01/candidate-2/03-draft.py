from opentrons import protocol_api

metadata = {
    "protocolName": "Prepare 12 Samples for SDS-PAGE",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    sample_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    dye_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)
    
    # Load instrument
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids and load them
    dye_liquid = protocol.define_liquid(name="dye", description="4x loading dye", display_color="#FF6600")
    dye_plate["A1"].load_liquid(liquid=dye_liquid, volume=100)
    
    for i in range(1, 13):
        sample_liquid = protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#FF0000")
        sample_plate[f"A{i}"].load_liquid(liquid=sample_liquid, volume=30)
    
    # Transfer sample and dye to destination plate without contaminating stocks
    for i in range(1, 13):
        # Transfer 15 µL sample
        p20.pick_up_tip()
        p20.aspirate(15, sample_plate[f"A{i}"])
        p20.dispense(15, dest_plate[f"A{i}"])
        p20.drop_tip()
        
        # Transfer 5 µL dye
        p20.pick_up_tip()
        p20.aspirate(5, dye_plate["A1"])
        p20.dispense(5, dest_plate[f"A{i}"], mix_after=(5, 16))
        p20.drop_tip()
