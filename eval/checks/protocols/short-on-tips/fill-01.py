from opentrons import protocol_api

metadata = {
    "protocolName": "Fill deep-well plate with LB and inoculate from glycerol stocks",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

LB_VOL = 500
INOC_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    tips300 = protocol.load_labware("opentrons_96_tiprack_300ul", 4)
    tips20 = protocol.load_labware("opentrons_96_tiprack_20ul", 5)
    deep = protocol.load_labware("nest_96_wellplate_2ml_deep", 1)
    stock = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 2)
    res = protocol.load_labware("nest_1_reservoir_195ml", 3)
    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips300])
    m20 = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tips20])

    res["A1"].load_liquid(protocol.define_liquid("LB medium", "Sterile LB medium", "#e6c229"), 60000)
    for w in stock.wells():
        w.load_liquid(protocol.define_liquid(
            f"Glycerol stock {w.well_name}", f"Glycerol stock in well {w.well_name}", "#8c564b"), 50)

    # 1) LB: one set of 8 tips for the whole plate. Wells are empty and the
    #    tips dispense from the top of the well, so they stay sterile/clean.
    m300.pick_up_tip()
    for col in deep.columns():
        for _ in range(2):
            m300.aspirate(LB_VOL / 2, res["A1"].bottom(2))
            m300.dispense(LB_VOL / 2, col[0].top(-5))
        m300.blow_out(col[0].top(-5))
    m300.drop_tip()

    # 2) Inoculate: every stock is a different strain -> new tips per column.
    m20.flow_rate.aspirate = 3.5   # glycerol stocks are viscous
    m20.flow_rate.dispense = 3.5
    for s_col, d_col in zip(stock.columns(), deep.columns()):
        m20.pick_up_tip()
        m20.mix(2, 10, s_col[0].bottom(1))
        m20.aspirate(INOC_VOL, s_col[0].bottom(1))
        protocol.delay(seconds=2)
        m20.dispense(INOC_VOL, d_col[0].bottom(3))
        m20.mix(3, 20, d_col[0].bottom(3), rate=2)
        m20.blow_out(d_col[0].top(-5))
        m20.drop_tip()
