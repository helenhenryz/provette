import opentrons

metadata = {"protocolName": "PCR setup 24 samples + NTC", "apiLevel": "2.19"}

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
    p300_single = protocol.load_instrument("p300_single_gen2", "left", tip_racks=[tip300])
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

    # ---- pool water (200 + 88.75) with fresh tips ----
    p300_single.pick_up_tip()
    p300_single.aspirate(200, water_rack["A1"])
    p300_single.dispense(200, pooled_tube)
    p300_single.drop_tip()

    p300_single.pick_up_tip()
    p300_single.aspirate(88.75, water_rack["A1"])
    p300_single.dispense(88.75, pooled_tube)
    p300_single.drop_tip()

    # ---- pool master mix (300 + 43.75) with fresh tips ----
    p300_single.pick_up_tip()
    p300_single.aspirate(300, mm_rack["A1"])
    p300_single.dispense(300, pooled_tube)
    p300_single.drop_tip()

    p300_single.pick_up_tip()
    p300_single.aspirate(43.75, mm_rack["A1"])
    p300_single.dispense(43.75, pooled_tube)
    p300_single.drop_tip()

    # mix pooled solution
    p300_single.pick_up_tip()
    for _ in range(3):
        p300_single.aspirate(200, pooled_tube)
        p300_single.dispense(200, pooled_tube)
    p300_single.drop_tip()

    # sample wells: rows A and B (indices 0 and 1) all columns 0-11 => 24 wells
    sample_wells = []
    for row in range(2):  # 0=A, 1=B
        for col in range(12):
            sample_wells.append(plate.wells()[row*12 + col])

    # NTC well: first well after sample wells in row-major order = C1 (row=2, col=0)
    ntc_well = plate.wells()[2*12 + 0]  # C1

    # distribute pooled mix (23 ul) to each sample well with fresh tip and mixing
    for well in sample_wells:
        p300_single.pick_up_tip()
        p300_single.aspirate(23, pooled_tube)
        p300_single.dispense(23, well)
        p300_single.mix(5, 20, well)
        p300_single.drop_tip()

    # dispense mix to NTC well (no sample)
    p300_single.pick_up_tip()
    p300_single.aspirate(23, pooled_tube)
    p300_single.dispense(23, ntc_well)
    p300_single.mix(5, 20, ntc_well)
    p300_single.drop_tip()

    # add 2 ul DNA samples to sample wells
    # Use tube wells in order A1..D6 (first 24) matching sample_wells order
    tube_wells = [
        f"{chr(65 + r)}{c+1}"
        for c in range(6)   # columns 1-6
        for r in range(4)   # rows A-D
    ][:24]  # exactly 24
    for well, tube_well in zip(sample_wells, tube_wells):
        p20_single.pick_up_tip()
        src = sample_rack[tube_well]
        p20_single.aspirate(2, src)
        p20_single.dispense(2, well)
        p20_single.mix(5, 20, well)
        p20_single.drop_tip()
