import math

metadata = {"protocolName": "Normalize DNA samples", "apiLevel": "2.19"}

def run(protocol):
    # Labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tiprack20 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tiprack300 = protocol.load_labware("opentrons_96_tiprack_300ul", 5)
    
    # Pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tiprack20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tiprack300])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    samples = []
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"DNA sample {i}", display_color="#FF0000")
        samples.append(liq)
    
    # Load initial liquids (source plate wells contain each sample)
    for i, well in enumerate(source_plate.wells()[:24]):
        well.load_liquid(samples[i], volume=200)  # enough volume
    
    # Water reservoir
    reservoir['A1'].load_liquid(water, volume=2000)
    
    dest_wells = dest_plate.wells()[:24]
    
    # Normalize each sample
    for i, (conc, src_well, dst_well) in enumerate(zip([85,120,44,67,210,95,33,150,78,60,101,55,190,72,48,130,88,25,64,110,39,175,92,58],
                                                      source_plate.wells()[:24],
                                                      dest_wells)):
        vol_sample = 500.0 / conc   # ul
        vol_water = 50.0 - vol_sample
        
        # Transfer sample with p20
        p20.pick_up_tip()
        p20.transfer(vol_sample, src_well, dst_well, new_tip='never')
        p20.drop_tip()
        
        # Transfer water with p300 (fresh tip)
        p300.pick_up_tip()
        p300.transfer(vol_water, reservoir['A1'], dst_well, new_tip='never')
        p300.drop_tip()
        
        # Mix to homogenize
        p300.pick_up_tip()
        p300.mix(5, 40, dst_well)  # 5 mixes of 40 ul (~80% of 50 ul)
        p300.drop_tip()
