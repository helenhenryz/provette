from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR_8cDNA_3genes",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # Define liquids with display_color
    sybr = protocol.define_liquid(name="sybr", description="2x SYBR Master Mix", display_color="#0000FF")
    fwd_1 = protocol.define_liquid(name="fwd 1", description="Forward primer 1", display_color="#0000FF")
    fwd_2 = protocol.define_liquid(name="fwd 2", description="Forward primer 2", display_color="#0000FF")
    fwd_3 = protocol.define_liquid(name="fwd 3", description="Forward primer 3", display_color="#0000FF")
    rev_1 = protocol.define_liquid(name="rev 1", description="Reverse primer 1", display_color="#0000FF")
    rev_2 = protocol.define_liquid(name="rev 2", description="Reverse primer 2", display_color="#0000FF")
    rev_3 = protocol.define_liquid(name="rev 3", description="Reverse primer 3", display_color="#0000FF")
    cdna_1 = protocol.define_liquid(name="cdna 1", description="cDNA sample 1", display_color="#0000FF")
    cdna_2 = protocol.define_liquid(name="cdna 2", description="cDNA sample 2", display_color="#0000FF")
    cdna_3 = protocol.define_liquid(name="cdna 3", description="cDNA sample 3", display_color="#0000FF")
    cdna_4 = protocol.define_liquid(name="cdna 4", description="cDNA sample 4", display_color="#0000FF")
    cdna_5 = protocol.define_liquid(name="cdna 5", description="cDNA sample 5", display_color="#0000FF")
    cdna_6 = protocol.define_liquid(name="cdna 6", description="cDNA sample 6", display_color="#0000FF")
    cdna_7 = protocol.define_liquid(name="cdna 7", description="cDNA sample 7", display_color="#0000FF")
    cdna_8 = protocol.define_liquid(name="cdna 8", description="cDNA sample 8", display_color="#0000FF")
    water = protocol.define_liquid(name="water", description="Nuclease-free water", display_color="#0000FF")

    # Load labware
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    tubes = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 2)
    tip_rack_1 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip_rack_2 = protocol.load_labware("opentrons_96_tiprack_20ul", 4)
    tip_rack_3 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    tip_rack_4 = protocol.load_labware("opentrons_96_tiprack_20ul", 6)
    tip_rack_5 = protocol.load_labware("opentrons_96_tiprack_20ul", 7)
    p20 = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip_rack_1, tip_rack_2, tip_rack_3, tip_rack_4, tip_rack_5])

    # Load liquids into source wells with sufficient margin
    tubes["A1"].load_liquid(liquid=sybr, volume=900)  # 10% margin added
    tubes["A2"].load_liquid(liquid=fwd_1, volume=40)
    tubes["A3"].load_liquid(liquid=fwd_2, volume=40)
    tubes["A4"].load_liquid(liquid=fwd_3, volume=40)
    tubes["A5"].load_liquid(liquid=rev_1, volume=40)
    tubes["A6"].load_liquid(liquid=rev_2, volume=40)
    tubes["B1"].load_liquid(liquid=rev_3, volume=40)
    tubes["B2"].load_liquid(liquid=cdna_1, volume=30)
    tubes["B3"].load_liquid(liquid=cdna_2, volume=30)
    tubes["B4"].load_liquid(liquid=cdna_3, volume=30)
    tubes["B5"].load_liquid(liquid=cdna_4, volume=30)
    tubes["B6"].load_liquid(liquid=cdna_5, volume=30)
    tubes["C1"].load_liquid(liquid=cdna_6, volume=30)
    tubes["C2"].load_liquid(liquid=cdna_7, volume=30)
    tubes["C3"].load_liquid(liquid=cdna_8, volume=30)
    tubes["C4"].load_liquid(liquid=water, volume=600)

    # Source well references
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

    # Destination wells
    dest_wells = list(plate.wells())[:81]

    # Transfer
    well_idx = 0
    for gene in [1, 2, 3]:
        # cDNA sample replicates
        for sample in range(1, 9):
            for rep in range(1, 4):
                dest_well = dest_wells[well_idx]
                # sybr
                p20.pick_up_tip()
                p20.aspirate(10, sybr_well)
                p20.dispense(10, dest_well)
                p20.drop_tip()
                # fwd primer
                p20.pick_up_tip()
                p20.aspirate(1, fwd_dict[str(gene)])
                p20.dispense(1, dest_well)
                p20.drop_tip()
                # rev primer
                p20.pick_up_tip()
                p20.aspirate(1, rev_dict[str(gene)])
                p20.dispense(1, dest_well)
                p20.drop_tip()
                # cDNA
                p20.pick_up_tip()
                p20.aspirate(2, cdna_dict[sample])
                p20.dispense(2, dest_well)
                p20.drop_tip()
                # water
                p20.pick_up_tip()
                p20.aspirate(6, water_well)
                p20.dispense(6, dest_well)
                p20.drop_tip()
                well_idx += 1
        # NTC replicates
        for rep in range(1, 4):
            dest_well = dest_wells[well_idx]
            # sybr
            p20.pick_up_tip()
            p20.aspirate(10, sybr_well)
            p20.dispense(10, dest_well)
            p20.drop_tip()
            # fwd primer
            p20.pick_up_tip()
            p20.aspirate(1, fwd_dict[str(gene)])
            p20.dispense(1, dest_well)
            p20.drop_tip()
            # rev primer
            p20.pick_up_tip()
            p20.aspirate(1, rev_dict[str(gene)])
            p20.dispense(1, dest_well)
            p20.drop_tip()
            # water for NTC
            p20.pick_up_tip()
            p20.aspirate(8, water_well)
            p20.dispense(8, dest_well)
            p20.drop_tip()
            well_idx += 1
