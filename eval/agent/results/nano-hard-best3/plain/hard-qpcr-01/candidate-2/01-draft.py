from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_8cDNA_3genes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    sybr = protocol.define_liquid(name="sybr", description="2x SYBR Master Mix", display_color='#1f77b4')
    fwd_1 = protocol.define_liquid(name="fwd 1", description="Forward primer 1", display_color='#ff7f0e')
    fwd_2 = protocol.define_liquid(name="fwd 2", description="Forward primer 2", display_color='#2ca02c')
    fwd_3 = protocol.define_liquid(name="fwd 3", description="Forward primer 3", display_color='#d62728')
    rev_1 = protocol.define_liquid(name="rev 1", description="Reverse primer 1", display_color='#9467bd')
    rev_2 = protocol.define_liquid(name="rev 2", description="Reverse primer 2", display_color='#8c564b')
    rev_3 = protocol.define_liquid(name="rev 3", description="Reverse primer 3", display_color='#e377c2')
    cdna_1 = protocol.define_liquid(name="cdna 1", description="cDNA sample 1", display_color='#17becf')
    cdna_2 = protocol.define_liquid(name="cdna 2", description="cDNA sample 2", display_color='#1f77b4')
    cdna_3 = protocol.define_liquid(name="cdna 3", description="cDNA sample 3", display_color='#ff7f0e')
    cdna_4 = protocol.define_liquid(name="cdna 4", description="cDNA sample 4", display_color='#2ca02c')
    cdna_5 = protocol.define_liquid(name="cdna 5", description="cDNA sample 5", display_color='#d62728')
    cdna_6 = protocol.define_liquid(name="cdna 6", description="cDNA sample 6", display_color='#9467bd')
    cdna_7 = protocol.define_liquid(name="cdna 7", description="cDNA sample 7", display_color='#8c564b')
    cdna_8 = protocol.define_liquid(name="cdna 8", description="cDNA sample 8", display_color='#e377c2')
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color='#17becf')

    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tips = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tips])

    # Load liquids into source wells
    tubes["A1"].load_liquid(liquid=sybr, volume=810)
    tubes["A2"].load_liquid(liquid=fwd_1, volume=27)
    tubes["A3"].load_liquid(liquid=fwd_2, volume=27)
    tubes["A4"].load_liquid(liquid=fwd_3, volume=27)
    tubes["A5"].load_liquid(liquid=rev_1, volume=27)
    tubes["A6"].load_liquid(liquid=rev_2, volume=27)
    tubes["B1"].load_liquid(liquid=rev_3, volume=27)
    tubes["B2"].load_liquid(liquid=cdna_1, volume=18)
    tubes["B3"].load_liquid(liquid=cdna_2, volume=18)
    tubes["B4"].load_liquid(liquid=cdna_3, volume=18)
    tubes["B5"].load_liquid(liquid=cdna_4, volume=18)
    tubes["B6"].load_liquid(liquid=cdna_5, volume=18)
    tubes["C1"].load_liquid(liquid=cdna_6, volume=18)
    tubes["C2"].load_liquid(liquid=cdna_7, volume=18)
    tubes["C3"].load_liquid(liquid=cdna_8, volume=18)
    tubes["C4"].load_liquid(liquid=water, volume=504)

    sybr_well = tubes["A1"]
    water_well = tubes["C4"]
    fwd_dict = {"1": tubes["A2"], "2": tubes["A3"], "3": tubes["A4"]}
    rev_dict = {"1": tubes["A5"], "2": tubes["A6"], "3": tubes["B1"]}
    cdna_dict = {
        1: tubes["B2"],
        2: tubes["B3"],
        3: tubes["B4"],
        4: tubes["B5"],
        5: tubes["B6"],
        6: tubes["C1"],
        7: tubes["C2"],
        8: tubes["C3"]
    }

    dest_wells = list(plate.wells())[:81]

    well_idx = 0
    for gene in [1,2,3]:
        # cDNA sample replicates
        for sample in range(1,9):
            for rep in range(1,4):
                dest_well = dest_wells[well_idx]
                p20.pick_up_tip()
                p20.aspirate(10, sybr_well)
                p20.dispense(10, dest_well)
                p20.aspirate(1, fwd_dict[str(gene)])
                p20.dispense(1, dest_well)
                p20.aspirate(1, rev_dict[str(gene)])
                p20.dispense(1, dest_well)
                p20.aspirate(2, cdna_dict[sample])
                p20.dispense(2, dest_well)
                p20.aspirate(6, water_well)
                p20.dispense(6, dest_well)
                p20.drop_tip()
                well_idx += 1
        # NTC replicates
        for rep in range(1,4):
            dest_well = dest_wells[well_idx]
            p20.pick_up_tip()
            p20.aspirate(10, sybr_well)
            p20.dispense(10, dest_well)
            p20.aspirate(1, fwd_dict[str(gene)])
            p20.dispense(1, dest_well)
            p20.aspirate(1, rev_dict[str(gene)])
            p20.dispense(1, dest_well)
            p20.aspirate(8, water_well)
            p20.dispense(8, dest_well)
            p20.drop_tip()
            well_idx += 1
