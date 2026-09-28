import json
from opentrons import protocol_api

metadata = {"protocolName": "PCR setup", "apiLevel": "2.19"}

def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    src_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 3)
    dst_plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 4)

    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    # define master mix liquid
    mm = protocol.define_liquid(name="master mix", description="PCR master mix", display_color="#FF0000")
    reservoir["A1"].load_liquid(liquid=mm, volume=2000)  # enough for 96*18=1728 ul

    # define template liquids (one per well)
    for col in range(1, 13):
        col_str = f"{col}"
        for row in "ABCDEFGH":
            well_name = f"{row}{col_str}"
            liq_name = f"template_{well_name}"
            liq = protocol.define_liquid(name=liq_name, description=f"Template {well_name}", display_color="#00FF00")
            src_plate[well_name].load_liquid(liquid=liq, volume=50)  # reasonable starting volume

    # distribute master mix using single tip (re-use)
    tip_wells = tips.wells()
    tip_idx = 0
    def get_tip():
        nonlocal tip_idx
        if tip_idx >= len(tip_wells):
            raise RuntimeError("Out of tips")
        tip = tip_wells[tip_idx]
        tip_idx += 1
        return tip

    p300.pick_up_tip(get_tip())
    wells_done = 0
    while wells_done < 96:
        # how many wells we can fill with current tip volume
        max_aspirate = p300.tip_rack.max_volume  # 300 ul
        batch = min(max_aspirate // 18, 96 - wells_done)
        vol_needed = batch * 18
        p300.aspirate(vol_needed, reservoir["A1"])
        for i in range(batch):
            dst_well = dst_plate.wells()[wells_done + i]
            p300.dispense(18, dst_well)
        p300.blow_out(reservoir["A1"])
        wells_done += batch
    p300.drop_tip()

    # add templates, fresh tip each well
    for col in range(1, 13):
        col_str = f"{col}"
        for row in "ABCDEFGH":
            src_well = f"{row}{col_str}"
            dst_well = f"{row}{col_str}"
            p300.pick_up_tip()
            p300.aspirate(2, src_plate[src_well])
            p300.dispense(2, dst_plate[dst_well])
            p300.drop_tip()
