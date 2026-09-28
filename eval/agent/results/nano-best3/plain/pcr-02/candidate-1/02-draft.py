from opentrons import protocol_api

metadata = {"protocolName": "PCR setup 25ul reactions", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 1)
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 3)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Define liquids
    master_mix = protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="Molecular biology grade water", display_color="#00FF00")
    
    sample_well_names = ["A1","A2","A3","A4","A5","A6","B1","B2","B3","B4","B5","B6","C1","C2","C3","C4","C5","C6","D1","D2","D3","D4","D5","D6"]
    sample_liquids = []
    for i, well in enumerate(sample_well_names):
        sample_liquid = protocol.define_liquid(name=f"sample {i+1}", description=f"Genomic DNA sample {i+1}", display_color="#FFFFFF")
        sample_liquids.append(sample_liquid)
        tuberack[well].load_liquid(liquid=sample_liquid, volume=20)
    
    # Load liquids into reservoirs and tube rack
    reservoir["A1"].load_liquid(liquid=master_mix, volume=500)
    reservoir["A2"].load_liquid(liquid=water, volume=300)

    # Fill plate wells
    for i, well_name in enumerate(sample_well_names):
        p20.pick_up_tip()
        p20.aspirate(12.5, reservoir["A1"])
        p20.dispense(12.5, plate[well_name])
        p20.aspirate(10.5, reservoir["A2"])
        p20.dispense(10.5, plate[well_name])
        p20.aspirate(2, tuberack[well_name])
        p20.dispense(2, plate[well_name])
        p20.drop_tip()
