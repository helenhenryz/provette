from opentrons import protocol_api

metadata = {
    "protocolName": "Fill 96‑well deep well plate with LB and inoculate from glycerol stock",
    "author": "Opentrons Helper",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware -------------------------------------------------
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    reservoir = protocol.load_labware('nest_1_reservoir_195ml', 2)
    glycerol_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 3)
    deepplate = protocol.load_labware('nest_96_wellplate_2ml_deep', 4)

    # ---- Liquids ------------------------------------------------
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

    # Pre‑load reagents on the deck
    # LB: need 96 wells × 500 µL = 48 mL → give a little extra for dead volume
    reservoir['A1'].load_liquid(lb, volume=50000)      # slightly more than required

    # Glycerol stock: realistic working volume per well
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    for col in range(1, 13):
        col_str = str(col)
        for r in rows:
            well = r + col_str
            glycerol_plate[well].load_liquid(gly, volume=100)

    # ---- Instrument ----------------------------------------------
    p300 = protocol.load_instrument('p300_multi_gen2',
                                    'right',
                                    tip_racks=[tips])

    # ---- Helper functions -----------------------------------------
    def fill_lb():
        """Fill each well of the deep‑well plate with 500 µL LB using the 8‑channel."""
        p300.pick_up_tip()
        src = reservoir['A1']
        for col in range(1, 13):
            col_str = str(col)
            # Destination wells for this column
            dest = [deepplate[r + col_str] for r in rows]
            # Deliver 250 µL twice → 500 µL per well
            p300.transfer(250, src, dest, new_tip='never')
            p300.transfer(250, src, dest, new_tip='never')
        p300.drop_tip()

    def inoculate():
        """Transfer 5 µL from each glycerol stock well to the matching deep‑well."""
        for col in range(1, 13):
            col_str = str(col)
            src_wells = [glycerol_plate[r + col_str] for r in rows]
            dst_wells = [deepplate[r + col_str] for r in rows]
            p300.pick_up_tip()
            p300.transfer(5, src_wells, dst_wells, new_tip='never')
            p300.drop_tip()

    # ---- Execution -----------------------------------------------
    fill_lb()
    inoculate()
