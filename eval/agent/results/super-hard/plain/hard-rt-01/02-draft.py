import json
from opentrons import protocol_api

metadata = {"protocolName": "Reverse transcription setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    rna_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)
    
    # pipettes
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips20])
    p300 = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tips300])
    
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
    tuberack["A1"].load_liquid(liquid=buffer, volume=500)   # buffer
    tuberack["A2"].load_liquid(liquid=rt, volume=200)       # rt
    tuberack["A3"].load_liquid(liquid=dntp, volume=200)     # dntp
    tuberack["A4"].load_liquid(liquid=primers, volume=200)  # primers
    tuberack["A5"].load_liquid(liquid=water, volume=500)    # water
    
    # RNA samples in plate: fill column-wise
    for i in range(1, 13):
        if i <= 8:
            well = f"{chr(ord('A')+i-1)}1"
        else:
            well = f"{chr(ord('A')+i-9)}2"
        rna_plate[well].load_liquid(liquid=rna_liquids[f"rna {i}"], volume=100)
    
    # master mix tubes
    mm_rt_tube = tuberack["B1"]
    mm_noRT_tube = tuberack["B2"]
    
    def transfer_small(src, vol, dest, pipette):
        pipette.pick_up_tip()
        pipette.aspirate(vol, src)
        pipette.dispense(vol, dest)
        pipette.drop_tip()
    
    def transfer_large(src, vol, dest, pipette):
        pipette.pick_up_tip()
        pipette.aspirate(vol, src)
        pipette.dispense(vol, dest)
        pipette.drop_tip()
    
    # Prepare RT master mix: water, buffer, dntp, primers, rt (enzyme last)
    transfer_large(tuberack["A5"], 66.0, mm_rt_tube, p300)   # water
    transfer_large(tuberack["A1"], 52.8, mm_rt_tube, p300)   # buffer
    transfer_large(tuberack["A3"], 13.2, mm_rt_tube, p300)   # dntp
    transfer_large(tuberack["A4"], 13.2, mm_rt_tube, p300)   # primers
    transfer_small(tuberack["A2"], 13.2, mm_rt_tube, p20)    # rt
    p300.pick_up_tip()
    p300.mix(5, 100.0, mm_rt_tube)  # mix volume within tip limit
    p300.drop_tip()
    
    # Prepare no-RT master mix: water, buffer, dntp, primers
    transfer_large(tuberack["A5"], 79.2, mm_noRT_tube, p300) # water
    transfer_large(tuberack["A1"], 52.8, mm_noRT_tube, p300) # buffer
    transfer_large(tuberack["A3"], 13.2, mm_noRT_tube, p300) # dntp
    transfer_large(tuberack["A4"], 13.2, mm_noRT_tube, p300) # primers
    p300.pick_up_tip()
    p300.mix(5, 100.0, mm_noRT_tube)
    p300.drop_tip()
    
    # well lists
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
    control_wells = first_n_wells(24)[12:]
    
    # dispense mixes and add RNA
    for i, (r_well, c_well) in enumerate(zip(reaction_wells, control_wells), start=1):
        # RT reaction: 12 ul mix + 8 ul RNA
        p300.pick_up_tip()
        p300.aspirate(12.0, mm_rt_tube)
        p300.dispense(12.0, dst_plate[r_well])
        p300.drop_tip()
        # RNA
        if i <= 8:
            rna_well = f"{chr(ord('A')+i-1)}1"
        else:
            rna_well = f"{chr(ord('A')+i-9)}2"
        p20.pick_up_tip()
        p20.aspirate(8.0, rna_plate[rna_well])
        p20.dispense(8.0, dst_plate[r_well])
        p20.drop_tip()
        # no-RT control
        p300.pick_up_tip()
        p300.aspirate(12.0, mm_noRT_tube)
        p300.dispense(12.0, dst_plate[c_well])
        p300.drop_tip()
        p20.pick_up_tip()
        p20.aspirate(8.0, rna_plate[rna_well])
        p20.dispense(8.0, dst_plate[c_well])
        p20.drop_tip()
    
    protocol.comment("Protocol completed")
