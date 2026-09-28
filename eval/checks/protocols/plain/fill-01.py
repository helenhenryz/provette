from opentrons import protocol_api

metadata = {
    "protocolName": "Deep-well LB fill and inoculation from glycerol stocks",
    "author": "Lab",
    "description": "500 ul LB per well of a 96 deep-well plate, then 5 ul inoculum from the matching glycerol stock well.",
}
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

LB_VOL = 500
INOC_VOL = 5


def run(protocol: protocol_api.ProtocolContext):
    # Labware
    deep_plate = protocol.load_labware("nest_96_wellplate_2ml_deep", 1, "Culture deep-well plate")
    stock_plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 2, "Glycerol stock plate")
    lb_res = protocol.load_labware("nest_1_reservoir_195ml", 3, "LB medium")
    tips300 = protocol.load_labware("opentrons_96_filtertiprack_200ul", 4)
    tips20 = protocol.load_labware("opentrons_96_filtertiprack_20ul", 5)

    m300 = protocol.load_instrument("p300_multi_gen2", "left", tip_racks=[tips300])
    m20 = protocol.load_instrument("p20_multi_gen2", "right", tip_racks=[tips20])

    lb = lb_res["A1"]

    # Liquids
    lb_liq = protocol.define_liquid(
        name="LB medium", description="Sterile LB medium (+ antibiotic); 48 ml needed", display_color="#E8C547"
    )
    lb.load_liquid(lb_liq, volume=60000)
    for i, well in enumerate(stock_plate.wells()):
        shade = format(40 + i * 2, "02X")
        liq = protocol.define_liquid(
            name=f"Glycerol stock {well.well_name}",
            description=f"Bacterial glycerol stock, well {well.well_name}",
            display_color=f"#8C{shade}4B",
        )
        well.load_liquid(liq, volume=100)

    # 1. 500 ul LB per well: 2 x 200 ul + 1 x 100 ul with filter tips, dispensed from
    #    the top of the (sterile, empty) wells so one set of tips can be used.
    m300.pick_up_tip()
    for col in deep_plate.rows()[0]:
        for vol in (200, 200, 100):
            m300.aspirate(vol, lb.bottom(2))
            m300.dispense(vol, col.top(-5))
        m300.blow_out(col.top(-5))
    m300.drop_tip()

    # 2. Inoculate well-to-well, fresh tips for every column. Glycerol stocks are viscous:
    #    mix first, aspirate slowly, and rinse the tips in the medium.
    for src, dest in zip(stock_plate.rows()[0], deep_plate.rows()[0]):
        m20.pick_up_tip()
        m20.mix(3, 15, src.bottom(1), rate=0.5)
        m20.aspirate(INOC_VOL, src.bottom(1), rate=0.3)
        protocol.delay(seconds=2)
        m20.dispense(INOC_VOL, dest.bottom(3), rate=0.5)
        m20.mix(3, 20, dest.bottom(3))
        m20.blow_out(dest.top(-10))
        m20.drop_tip()

    protocol.comment("Done. Cover with a breathable seal and incubate with shaking.")
