from opentrons import protocol_api

metadata = {
    "protocolName": "Fill 96‑well deep well plate with LB and inoculate from glycerol stock",
    "author": "Opentrons Helper",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.Context):
    # ----- Labware -------------------------------------------------
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2)
    glycerol_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 3)
    deepplate = protocol.load_labware('nest_96_wellplate_2ml_deep', 4)

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

    # Load LB into reservoir (~50 mL gives plenty for 96*500 µL plus overhead)
    reservoir['A1'].load_liquid(lb, volume=50000)

    # Realistic volume per well in glycerol stock plate
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    for col in range(1, 13):
        col_str = str(col)
        for r in rows:
            well = r + col_str
            glycerol_plate[well].load_liquid(glyc, volume=100)

    # ----- Instrument -----------------------------------------------
    p300 = protocol.load_instrument('p300_multi_gen2',
                                    'right',
                                    tip_racks=[tips])

    # ----- Protocol steps -------------------------------------------
    def fill_lb():
        """Fill each well of the deep‑well plate with 500 µL LB via 8‑channel."""
        p300.pick_up_tip()
        src = reservoir['A1']
        for col in range(1, 13):
            col_str = str(col)
            # All rows in current column
            dest = [deepplate[r + col_str] for r in rows]
            # Two aliquots of 250 µL => 500 µL total per well
            p300.transfer(250, src, dest, new_tip='never')
            p300.transfer(250, src, dest, new_tip='never')
        p300.drop_tip()

    def inoculate():
        """Transfer 5 µL from each glycerol well to the matching deep‑well well."""
        for col in range(1, 13):
            col_str = str(col)
            src_wells = [glycerol_plate[r + col_str] for r in rows]
            dst_wells = [deepplate[r + col_str] for r in rows]
            p300.pick_up_tip()
            p300.transfer(5, src_wells, dst_wells, new_tip='never')
            p300.drop_tip()

    # Run the workflow
    fill_lb()
    inoculate()
