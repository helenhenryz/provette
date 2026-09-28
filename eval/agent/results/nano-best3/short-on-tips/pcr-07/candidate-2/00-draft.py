from opentrons import protocol_api

metadata = {"protocolName": "PCR Assembly", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids
    buffer = protocol.define_liquid(name="buffer", description="buffer mix", display_color="#0000FF")
    polymerase = protocol.define_liquid(name="polymerase", description="polymerase", display_color="#00FF00")
    fwd_primer = protocol.define_liquid(name="fwd primer", description="forward primer", display_color="#008800")
    rev_primer = protocol.define_liquid(name="rev primer", description="reverse primer", display_color="#000088")
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    # Define samples
    samples = []
    for i in range(1,13):
        sample = protocol.define_liquid(name=f"sample {i}", description=f"sample {i}", display_color=f"#{i:06X}")
        samples.append(sample)
    # Load modules and labware
    temp_mod = protocol.load_module("temperature module gen2", 1)
    block = temp_mod.load_labware("opentrons_24_aluminumblock_nest_1.5ml_snapcap")
    plate = protocol.load_labware("biorad_96_wellplate_200ul_pcr", "2")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "3")
    # Load tip racks
    tiprack_300 = protocol.load_labware("opentrons_96_tiprack_300ul", "4")
    tiprack_20 = protocol.load_labware("opentrons_96_tiprack_20ul", "5")
    # Load pipettes
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tiprack_300])
    p20 = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tiprack_20])
    # Load liquids into block wells
    block["A1"].load_liquid(liquid=buffer, volume=150)
    block["A2"].load_liquid(liquid=polymerase, volume=10)
    block["A3"].load_liquid(liquid=fwd_primer, volume=15)
    block["A4"].load_liquid(liquid=rev_primer, volume=15)
    block["A5"].load_liquid(liquid=water, volume=150)
    sample_well_names = ["A6", "B1", "B2", "B3", "B4", "B5", "B6", "C1", "C2", "C3", "C4", "C5"]
    for i, well_name in enumerate(sample_well_names):
        block[well_name].load_liquid(liquid=samples[i], volume=20)
    # Define master mix pool well
    master_mix_pool = reservoir["A1"]
    # Pool components into master_mix_pool
    p300.pick_up_tip()
    p300.aspirate(132, block["A1"])
    p300.dispense(132, master_mix_pool)
    p300.aspirate(138.6, block["A5"])
    p300.dispense(138.6, master_mix_pool)
    p20.pick_up_tip()
    p20.aspirate(6.6, block["A2"])
    p20.dispense(6.6, master_mix_pool)
    p20.aspirate(13.2, block["A3"])
    p20.dispense(13.2, master_mix_pool)
    p20.aspirate(13.2, block["A4"])
    p20.dispense(13.2, master_mix_pool)
    # Aspirate master mix into tip
    p300.aspirate(23.0, master_mix_pool)
    # Dispense into each reaction well
    for i in range(12):
        p300.dispense(23.0, plate[f"A{i+1}"])
        if i < 11:
            p300.aspirate(23.0, master_mix_pool)
    p300.drop_tip()
    # Add samples
    for i in range(12):
        p20.aspirate(2, block[sample_well_names[i]])
        p20.dispense(2, plate[f"A{i+1}"])
    p20.drop_tip()
