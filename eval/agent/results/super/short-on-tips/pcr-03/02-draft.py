from opentrons import protocol_api

metadata = {"protocolName": "PCR setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    src_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    # instruments
    p300_single = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])
    p300_multi = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips])

    # liquids
    mm = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    reservoir["A1"].load_liquid(liquid=mm, volume=2000)

    for col in range(1, 13):
        col_str = f"{col}"
        for row in "ABCDEFGH":
            well = f"{row}{col_str}"
            liq_name = f"template_{well}"
            liq = protocol.define_liquid(name=liq_name, description=f"Template {well}", display_color="#00FF00")
            src_plate[well].load_liquid(liquid=liq, volume=50)

    # ---- master mix distribution (single channel, reuse tip) ----
    p300_single.pick_up_tip()
    wells_done = 0
    while wells_done < 96:
        batch = min(300 // 18, 96 - wells_done)  # 16 wells per aspiration
        vol = batch * 18
        p300_single.aspirate(vol, reservoir["A1"])
        for i in range(batch):
            dst_well = dst_plate.wells()[wells_done + i]
            p300_single.dispense(18, dst_well)
        p300_single.blow_out(reservoir["A1"])
        wells_done += batch
    p300_single.drop_tip()

    # ---- template addition (8-channel) ----
    # process in columns of 8
    for col in range(1, 13):
        col_str = f"{col}"
        # select source and destination columns as lists of wells
        src_column = [src_plate[f"{row}{col_str}"] for row in "ABCDEFGH"]
        dst_column = [dst_plate[f"{row}{col_str}"] for row in "ABCDEFGH"]
        p300_multi.pick_up_tip()
        p300_multi.aspirate(2, src_column)
        p300_multi.dispense(2, dst_column)
        p300_multi.drop_tip()
