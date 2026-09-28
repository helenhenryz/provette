from opentrons import protocol_api

metadata = {"protocolName": "PCR setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # labware
    tips1 = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    tips2 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    src_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 5)

    # instruments
    p300_single = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips1, tips2])
    p20_single = protocol.load_instrument("p20_single_gen2", "left", tip_racks=[tips1, tips2])

    # liquids
    mm = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    water = protocol.define_liquid(name="water", description="NTC water", display_color="#0000FF")
    reservoir["A1"].load_liquid(liquid=mm, volume=2000)          # master mix
    reservoir["A2"].load_liquid(liquid=water, volume=500)       # enough water for NTC and depth

    # template liquids (one per well)
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

    # ---- template addition (p20, fresh tip each well) ----
    for col in range(1, 13):
        col_str = f"{col}"
        for row in "ABCDEFGH":
            if row == "H" and col_str == "12":
                # H12 is NTC: skip template addition here
                continue
            src_well = f"{row}{col_str}"
            dst_well = f"{row}{col_str}"
            p20_single.pick_up_tip()
            p20_single.aspirate(2, src_plate[src_well])
            p20_single.dispense(2, dst_plate[dst_well])
            p20_single.mix(repetitions=5, volume=16, location=dst_plate[dst_well])
            p20_single.drop_tip()

    # ---- add NTC water to H12 ----
    p20_single.pick_up_tip()
    p20_single.aspirate(2, reservoir["A2"])
    p20_single.dispense(2, dst_plate["H12"])
    p20_single.mix(repetitions=5, volume=16, location=dst_plate["H12"])
    p20_single.drop_tip()
