from opentrons import protocol_api
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

    # pool master mix (split due to tip limit)
    p300_single.pick_up_tip()
    p300_single.aspirate(300, mm_rack["A1"])
    p300_single.dispense(300, pooled_tube)
    p300_single.aspirate(30, mm_rack["A1"])
    p300_single.dispense(30, pooled_tube)
    p300_single.drop_tip()

    # pool water
    p300_single.pick_up_tip()
    p300_single.aspirate(277.2, water_rack["A1"])
    p300_single.dispense(277.2, pooled_tube)
    p300_single.drop_tip()

    # mix pooled solution
    p300_single.pick_up_tip()
    for _ in range(3):
        p300_single.aspirate(200, pooled_tube)
        p300_single.dispense(200, pooled_tube)
    p300_single.drop_tip()

    # distribute pooled mix (23 ul) to each well with fresh tip and mixing
    for well in plate.wells()[:24]:
        p300_single.pick_up_tip()
        p300_single.aspirate(23, pooled_tube)
        p300_single.dispense(23, well)
        # mix after dispensing
        p300_single.mix(5, 20, well)
        p300_single.drop_tip()

    # add 2 ul DNA samples with fresh tip and mixing
    for i, well in enumerate(plate.wells()[:24]):
        p20_single.pick_up_tip()
        src_well = sample_rack.wells()[i]
        p20_single.aspirate(2, src_well)
        p20_single.dispense(2, well)
        p20_single.mix(5, 20, well)
        p20_single.drop_tip()
