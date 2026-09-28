from opentrons import protocol_api

metadata = {"protocolName": "RT_reverse_transcription", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x RT buffer", display_color="#0000FF")
    rt = protocol.define_liquid(name="rt", description="Reverse transcriptase", display_color="#00FF00")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFA500")
    primers = protocol.define_liquid(name="primers", description="Random primers", display_color="#800080")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#00FFFF")
    
    # Load labware
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])
    
    # Load temperature module and block
    temp_module = protocol.load_module("temperature module gen2", 2)
    block = temp_module.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    
    # Load source plate with RNA samples
    rna_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    
    # Load destination plate (PCR plate)
    dest_plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", 4)
    
    # Load liquids into source wells
    block["A1"].load_liquid(liquid=buffer, volume=200)
    block["A2"].load_liquid(liquid=rt, volume=50)
    block["A3"].load_liquid(liquid=dntp, volume=100)
    block["A4"].load_liquid(liquid=primers, volume=100)
    block["A5"].load_liquid(liquid=water, volume=500)
    
    # Load RNA samples into plate wells (increase volume to avoid shallow liquid)
    for i in range(1, 13):
        rna_liquid = protocol.define_liquid(name=f"rna {i}", description=f"RNA sample {i}", display_color=f"#{i*100:03X}")
        rna_plate[f"A{i}"].load_liquid(liquid=rna_liquid, volume=60)  # increased volume
    
    # Iterate over destination wells (first 24)
    for i, well in enumerate(dest_plate.wells()[:24]):
        if i < 12:
            # Reaction well
            # 4 ul buffer
            p20.pick_up_tip()
            p20.aspirate(4, block["A1"])
            p20.dispense(4, well)
            p20.drop_tip()
            # 5 ul water
            p20.pick_up_tip()
            p20.aspirate(5, block["A5"])
            p20.dispense(5, well)
            p20.drop_tip()
            # 1 ul dntp
            p20.pick_up_tip()
            p20.aspirate(1, block["A3"])
            p20.dispense(1, well)
            p20.drop_tip()
            # 1 ul primers
            p20.pick_up_tip()
            p20.aspirate(1, block["A4"])
            p20.dispense(1, well)
            p20.drop_tip()
            # 8 ul rna
            p20.pick_up_tip()
            p20.aspirate(8, rna_plate[f"A{i+1}"])
            p20.dispense(8, well)
            p20.drop_tip()
            # 1 ul rt (last)
            p20.pick_up_tip()
            p20.aspirate(1, block["A2"])
            p20.dispense(1, well)
            p20.drop_tip()
        else:
            # No-RT control well
            control_index = i - 12 + 1
            # 4 ul buffer
            p20.pick_up_tip()
            p20.aspirate(4, block["A1"])
            p20.dispense(4, well)
            p20.drop_tip()
            # 6 ul water
            p20.pick_up_tip()
            p20.aspirate(6, block["A5"])
            p20.dispense(6, well)
            p20.drop_tip()
            # 1 ul dntp
            p20.pick_up_tip()
            p20.aspirate(1, block["A3"])
            p20.dispense(1, well)
            p20.drop_tip()
            # 1 ul primers
            p20.pick_up_tip()
            p20.aspirate(1, block["A4"])
            p20.dispense(1, well)
            p20.drop_tip()
            # 8 ul rna
            p20.pick_up_tip()
            p20.aspirate(8, rna_plate[f"A{control_index}"])
            p20.dispense(8, well)
            p20.drop_tip()
