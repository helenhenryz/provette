import json
from opentrons import protocol_api

metadata = {"protocolName": "Reverse transcription setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    rna_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # define liquids
    buffer = protocol.define_liquid(name="buffer", description="5x RT buffer", display_color="#00FF00")
    rt = protocol.define_liquid(name="rt", description="Reverse transcriptase", display_color="#FF0000")
    dntp = protocol.define_liquid(name="dntp", description="dNTP mix", display_color="#FFFF00")
    primers = protocol.define_liquid(name="primers", description="Random primers", display_color="#00FFFF")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#FFFFFF")
    rna_liquids = {}
    for i in range(1, 13):
        name = f"rna {i}"
        liq = protocol.define_liquid(name=name, description=f"RNA sample {i}", display_color="#FFA500")
        rna_liquids[name] = liq
    
    # load liquids into sources
    # tubes positions: assign arbitrarily
    tuberack["A1"].load_liquid(liquid=buffer, volume=500)   # buffer
    tuberack["A2"].load_liquid(liquid=rt, volume=200)       # rt
    tuberack["A3"].load_liquid(liquid=dntp, volume=200)     # dntp
    tuberack["A4"].load_liquid(liquid=primers, volume=200)  # primers
    tuberack["A5"].load_liquid(liquid=water, volume=500)    # water
    
    # RNA samples in plate: each well gets 100 ul
    for i in range(1,13):
        well = f"{chr(ord('A')+(i-1)%8)}{1+(i-1)//8}"  # A1..H2 etc but ensure 12 unique
        # simpler: fill first column then second
        if i <=8:
            well = f"{chr(ord('A')+i-1)}1"
        else:
            well = f"{chr(ord('A')+i-9)}2"
        rna_plate[well].load_liquid(liquid=rna_liquids[f"rna {i}"], volume=100)
    
    # prepare master mix tubes
    mm_rt_tube = tuberack["B1"]
    mm_noRT_tube = tuberack["B2"]
    
    # helper to transfer with new tip
    def transfer_with_tip(src, vol, dest, mix_after=False):
        p300.pick_up_tip()
        p300.aspirate(vol, src)
        p300.dispense(vol, dest)
        if mix_after:
            p300.mix(3, vol*0.5, dest)
        p300.drop_tip()
    
    # prepare RT master mix
    # buffer 52.8, rt 13.2, dntp 13.2, primers 13.2, water 66.0
    transfer_with_tip(tuberack["A1"], 52.8, mm_rt_tube)
    transfer_with_tip(tuberack["A2"], 13.2, mm_rt_tube)
    transfer_with_tip(tuberack["A3"], 13.2, mm_rt_tube)
    transfer_with_tip(tuberack["A4"], 13.2, mm_rt_tube)
    transfer_with_tip(tuberack["A5"], 66.0, mm_rt_tube, mix_after=True)
    
    # prepare no-RT master mix
    # buffer 52.8, dntp 13.2, primers 13.2, water 79.2
    transfer_with_tip(tuberack["A1"], 52.8, mm_noRT_tube)
    transfer_with_tip(tuberack["A3"], 13.2, mm_noRT_tube)
    transfer_with_tip(tuberack["A4"], 13.2, mm_noRT_tube)
    transfer_with_tip(tuberack["A5"], 79.2, mm_noRT_tube, mix_after=True)
    
    # define well lists
    def first_n_wells(n):
        wells = []
        col = 1
        while len(wells) < n:
            for row in ['A','B','C','D','E','F','G','H']:
                wells.append(f"{row}{col}")
                if len(wells) >= n:
                    break
            col += 1
        return wells[:n]
    
    reaction_wells = first_n_wells(12)
    control_wells = first_n_wells(24)[12:]  # next 12 after first 12
    
    # dispense mixes and add RNA
    for i, (r_well, c_well) in enumerate(zip(reaction_wells, control_wells), start=1):
        # RT reaction
        p300.pick_up_tip()
        p300.aspirate(12.0, mm_rt_tube)
        p300.dispense(12.0, dst_plate[r_well])
        p300.drop_tip()
        # add RNA
        rna_well = f"{chr(ord('A')+(i-1)%8)}{1+(i-1)//8}" if i<=8 else f"{chr(ord('A')+i-9)}2"
        p300.pick_up_tip()
        p300.aspirate(8.0, rna_plate[rna_well])
        p300.dispense(8.0, dst_plate[r_well])
        p300.drop_tip()
        # no-RT control
        p300.pick_up_tip()
        p300.aspirate(12.0, mm_noRT_tube)
        p300.dispense(12.0, dst_plate[c_well])
        p300.drop_tip()
        p300.pick_up_tip()
        p300.aspirate(8.0, rna_plate[rna_well])
        p300.dispense(8.0, dst_plate[c_well])
        p300.drop_tip()
    
    # final note
    protocol.comment("Protocol completed")
