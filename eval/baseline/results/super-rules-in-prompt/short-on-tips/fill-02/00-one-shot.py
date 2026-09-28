from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein stock into PCR strip tubes",
    "author": "",
    "description": "Aliquot 50 µL of a 15 mL protein stock into 48 PCR strip tubes on an aluminium block.",
    "apiLevel": "2.19"
}


def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware('opentrons_96_tiprack_1000ul', 1)
    tuberack = protocol.load_labware('opentrons_24_tuberack_falcon_15ml_conical', 2)
    pcr_block = protocol.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', 3
    )

    # ----- Liquids -----
    protein = protocol.define_liquid(
        name='protein',
        description='Protein stock for aliquoting',
        display_color='#00A86B'  # a pleasant green
    )
    # Assume the tube starts with ~3 mL, plenty for the 48×50 µL aliquot (+ excess)
    protein_well = tuberack['A1']
    protein_well.load_liquid(liquid=protein, volume=3000)  # 3 mL

    # ----- Instrument -----
    p1000 = protocol.load_instrument('p1000_single_gen2', 'right', tip_racks=[tiprack])

    # ----- Destination wells (48 wells) -----
    # Use first six columns (cols 1‑6) of the 96‑well layout → 8 rows × 6 cols = 48 wells
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    cols = [str(c) for c in range(1, 7)]  # '1' … '6'
    dest_wells = [f"{r}{c}" for r in rows for c in cols]  # length 48

    # ----- Aliquoting -----
    wells_per_tip = 20                     # 1000 µL / 50 µL per well
    total_wells = len(dest_wells)
    for start in range(0, total_wells, wells_per_tip):
        batch = dest_wells[start:start + wells_per_tip]
        # Aspirate enough for the whole batch (≤1000 µL)
        vol_needed = len(batch) * 50
        p1000.pick_up_tip()
        p1000.aspirate(vol_needed, protein_well)
        for well in batch:
            p1000.dispense(50, pcr_block[well])
        p1000.drop_tip()


# End of protocol
