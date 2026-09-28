from opentrons import protocol_api

metadata = {
    "protocolName": "Fill 96‑well deep‑well plate with LB and inoculate from glycerol stock",
    "author": "Opentrons Helper",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -------------------------------------------------
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', 1)   # for p300
    tips_20  = protocol.load_labware('opentrons_96_tiprack_20ul', 2)    # for p20
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 3)
    glycerol_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 4)
    deepplate = protocol.load_labware('nest_96_wellplate_2ml_deep', 5)

    # ----- Liquids -------------------------------------------------
    lb = protocol.define_liquid(
        name='lb',
        description='Luria–Broth medium',
        display_color='#FFA500'
    )
    glyc = protocol.define_liquid(
        name='glycerol_stock',
        description='Glycerol stock of strains',
        display_color='#00AA00'
    )

    # Reservoir: enough LB for 96 wells × 500 µL = 48 mL + excess
    reservoir['A1'].load_liquid(lb, volume=50000)

    # Glycerol stock plate: realistic working volume per well
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    for col in range(1, 13):
        col_str = str(col)
        for r in rows:
            glycerol_plate[r + col_str].load_liquid(glyc, volume=100)

    # ----- Instruments ---------------------------------------------
    p300 = protocol.load_instrument('p300_multi_gen2',
                                    'right',
                                    tip_racks=[tips_300])
    p20  = protocol.load_instrument('p20_multi_gen2',
                                    'right',
                                    tip_racks=[tips_20])

    # ----- Protocol steps -------------------------------------------
    def fill_lb():
        """Fill each well of the deep‑well plate with 500 µL LB using the 8‑channel p300."""
        p300.pick_up_tip()
        src = reservoir['A1']
        for col in range(1, 13):
            col_str = str(col)
            dest = [deepplate[r + col_str] for r in rows]   # 8 wells in column
            # Two aliquots of 250 µL → 500 µL per well
            p300.transfer(250, src, dest, new_tip='never')
            p300.transfer(250, src, dest, new_tip='never')
        p300.drop_tip()

    def inoculate():
        """Transfer 5 µL from each glycerol well to the matching deep‑well well."""
        for col in range(1, 13):
            col_str = str(col)
            src_wells = [glycerol_plate[r + col_str] for r in rows]
            dst_wells = [deepplate[r + col_str] for r in rows]
            p20.pick_up_tip()
            p20.transfer(5, src_wells, dst_wells, new_tip='never')
            p20.drop_tip()

    # ----- Execute --------------------------------------------------
    fill_lb()
    inoculate()
