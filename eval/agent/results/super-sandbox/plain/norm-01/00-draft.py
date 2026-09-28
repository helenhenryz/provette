import math

metadata = {"protocolName": "Normalize DNA samples", "apiLevel": "2.19"}

def run(protocol):
    # Labware
    source_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 1)
    dest_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 3)
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    
    # Pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # Define liquids
    water = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#FFFFFF")
    samples = []
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"DNA sample {i}", display_color="#FF0000")
        samples.append(liq)
    
    # Load initial liquids (starting volumes)
    # Source plate wells contain each sample at given concentration; volume arbitrary but enough
    sample_conc = [85,120,44,67,210,95,33,150,78,60,101,55,190,72,48,130,88,25,64,110,39,175,92,58]
    for i, well in enumerate(source_plate.wells()[:24]):
        well.load_liquid(samples[i], volume=200)  # enough for transfers
    
    # Water reservoir: load water in well A1
    reservoir['A1'].load_liquid(water, volume=2000)
    
    # Map destination wells order A1..H12 column-wise? In platemap notes: order in number order (1,2,3...) reading down columns or along rows.
    # We'll just use wells() which yields A1..H12 column-wise (A1,A2...).
    dest_wells = dest_plate.wells()[:24]
    
    # Perform normalizations
    for i, (conc, src_well, dst_well) in enumerate(zip(sample_conc, source_plate.wells()[:24], dest_wells)):
        # calculate sample volume needed to get 10 ng/ul in 50 ul: Vsample = (target * final_vol) / conc = (10*50)/conc = 500/conc
        vol_sample = 500.0 / conc
        vol_water = 50.0 - vol_sample
        # pick up tip
        p300.pick_up_tip()
        # transfer sample
        p300.transfer(vol_sample, src_well, dst_well, new_tip='never')
        # transfer water
        p300.transfer(vol_water, reservoir['A1'], dst_well, new_tip='never')
        p300.drop_tip()
        
        # Optional mix after both additions
        p300.pick_up_tip()
        p300.mix(3, 25, dst_well)
        p300.drop_tip()
