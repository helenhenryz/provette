import opentrons

metadata = {"protocolName": "PCR setup 24 samples", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # tip racks
    tip20 = protocol.load_labware("opentrons_96_tiprack_20ul", 1)
    tip300 = protocol.load_labware("opentrons_96_tiprack_300ul", 2)
    # tube racks
    mm_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 3)
    water_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 4)
    sample_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 5)
    pool_rack = protocol.load_labware("opentrons_24_tuberack_nest_1.5ml_snapcap", 6)
    # PCR plate
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 7)

    # pipettes
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tip300])
    p20_single = protocol.load_instrument("p20_single_gen2", "right", tip_racks=[tip20])

    # define liquids
    mm_liq = protocol.define_liquid(name="master mix", description="2x PCR master mix with primers", display_color="#FF0000")
    water_liq = protocol.define_liquid(name="water", description="nuclease-free water", display_color="#0000FF")
    sample_liqs = []
    for i in range(1, 25):
        liq = protocol.define_liquid(name=f"sample {i}", description=f"Genomic DNA sample {i}", display_color="#00FF00")
        sample_liqs.append(liq)

    # load liquids into sources
    mm_rack["A1"].load_liquid(liquid=mm_liq, volume=500)  # enough for pooling
    water_rack["A1"].load_liquid(liquid=water_liq, volume=500)
    for i in range(24):
        sample_rack[f"{chr(65 + i//6)}{(i%6)+1}"].load_liquid(liquid=sample_liqs[i], volume=50)

    # pooled mix tube (empty initially)
    pooled_tube = pool_rack["A1"]

    # pool master mix
    p300_multi.pick_up_tip()
    p300_multi.aspirate(330, mm_rack["A1"])
    p300_multi.dispense(330, pooled_tube)
    p300_multi.drop_tip()

    # pool water
    p300_multi.pick_up_tip()
    p300_multi.aspirate(277.2, water_rack["A1"])
    p300_multi.dispense(277.2, pooled_tube)
    p300_multi.drop_tip()

    # mix pooled solution
    p300_multi.pick_up_tip()
    for _ in range(3):
        p300_multi.aspirate(200, pooled_tube)
        p300_multi.dispense(200, pooled_tube)
    p300_multi.drop_tip()

    # distribute pooled mix (23 ul) to wells A1..C12 (24 wells)
    cols = [0, 1, 2]  # columns 1-3
    for col in cols:
        p300_multi.pick_up_tip()
        p300_multi.aspirate(23, pooled_tube)
        for row in range(8):  # A-H
            well = plate.wells()[row*12 + col]
            p300_multi.dispense(23, well)
        p300_multi.drop_tip()

    # add 2 ul DNA samples
    for i in range(24):
        p20_single.pick_up_tip()
        src_well = sample_rack.wells()[i]
        dst_well = plate.wells()[i]
        p20_single.aspirate(2, src_well)
        p20_single.dispense(2, dst_well)
        p20_single.drop_tip()
