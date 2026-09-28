import json
from opentrons import protocol_api

metadata = {"protocolName": "Bradford assay 20 samples duplicate", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # define liquids
    liquids = {
        "bradford": protocol.define_liquid(name="bradford", description="Bradford reagent", display_color="#FF0000"),
        "standard 1": protocol.define_liquid(name="standard 1", description="BSA standard 1", display_color="#FFA500"),
        "standard 2": protocol.define_liquid(name="standard 2", description="BSA standard 2", display_color="#FFA500"),
        "standard 3": protocol.define_liquid(name="standard 3", description="BSA standard 3", display_color="#FFA500"),
        "standard 4": protocol.define_liquid(name="standard 4", description="BSA standard 4", display_color="#FFA500"),
        "standard 5": protocol.define_liquid(name="standard 5", description="BSA standard 5", display_color="#FFA500"),
        "standard 6": protocol.define_liquid(name="standard 6", description="BSA standard 6", display_color="#FFA500"),
        "standard 7": protocol.define_liquid(name="standard 7", description="BSA standard 7", display_color="#FFA500"),
        "standard 8": protocol.define_liquid(name="standard 8", description="BSA standard 8", display_color="#FFA500"),
        **{f"sample {i}": protocol.define_liquid(name=f"sample {i}", description=f"Protein sample {i}", display_color="#0000FF") for i in range(1, 21)}
    }
    
    # load labware
    plate = protocol.load_labware("nest_96_wellplate_2ml_deep", "1")
    tuberack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", "2")
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "3")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "4")
    
    # pipette
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    
    # load liquids into sources
    # samples in tuberack: map 1-20 to wells A1-D6
    rows = ['A','B','C','D']
    for i in range(1, 21):
        idx = i-1
        row = rows[idx % 4]
        col = (idx // 4) + 1
        tube = tuberack[f"{row}{col}"]
        tube.load_liquid(liquids[f"sample {i}"], volume=500)  # ul
    
    # Bradford reagent in reservoir A1
    reservoir["A1"].load_liquid(liquids["bradford"], volume=15000)  # ul
    
    # load standards into plate column 1 (A1-H1) each 50 ul
    for i, row in enumerate("ABCDEFGH", start=1):
        well = plate[f"{row}1"]
        well.load_liquid(liquids[f"standard {i}"], volume=50)
    
    # prepare list of destination wells for sample duplicates (columns 2-6, rows A-H)
    dest_wells = []
    for col in range(2, 7):  # columns 2-6
        for row in "ABCDEFGH":
            dest_wells.append(f"{row}{col}")
    
    # transfer 5 ul of each sample to two duplicate wells
    for i in range(1, 21):
        idx = i-1
        src_row = rows[idx % 4]
        src_col = (idx // 4) + 1
        src = tuberack[f"{src_row}{src_col}"]
        w1 = plate[dest_wells[2*(i-1)]]
        w2 = plate[dest_wells[2*(i-1)+1]]
        p300.pick_up_tip()
        p300.transfer(5, src, w1, new_tip=False)
        p300.transfer(5, src, w2, new_tip=False)
        p300.drop_tip()
    
    # add 250 ul Bradford to all used wells: standards column1 and all sample duplicate wells
    used_wells = [plate[f"{row}1"] for row in "ABCDEFGH"]  # standards
    used_wells += [plate[well] for well in dest_wells]      # sample duplicates
    
    p300.pick_up_tip()
    for well in used_wells:
        p300.transfer(250, reservoir["A1"], well, new_tip=False, mix_after=(2, 100))
    p300.drop_tip()
