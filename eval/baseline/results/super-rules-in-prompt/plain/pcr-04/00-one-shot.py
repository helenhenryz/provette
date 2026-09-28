from opentrons import protocol_api

metadata = {
    "protocolName": "qPCR Plate Setup",
    "author": "Assistant",
    "description": "Prepare a qPCR plate with six cDNA samples in triplicate (8 µL master mix + 2 µL sample per well).",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---- Labware -----------------------------------------------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', 1)
    # Aluminium block holding PCR‑style strips for the samples
    sample_block = protocol.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul', 2)
    # Rack holding a 2 mL tube with master mix
    mm_rack = protocol.load_labware('opentrons_24_tuberack_nest_2ml_snapcap', 3)
    # Destination qPCR plate
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 4)

    # ---- Liquids -----------------------------------------------------------
    master_mix_def = protocol.define_liquid(
        name='master mix',
        description='SYBR green master mix with primers',
        display_color='#FFFF00'
    )
    sample_defs = [
        protocol.define_liquid(
            name=f'sample {i}',
            description=f'cDNA sample {i}',
            display_color='#87CEEB'
        )
        for i in range(1, 7)
    ]
    # Map sample positions on the block to their liquid objects
    sample_positions = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6']
    sample_liq_map = dict(zip(sample_positions, sample_defs))  # position -> liquid

    # Load liquids onto the labware on the deck
    # Master mix: place in first well of the 2 mL tube rack
    mm_source = mm_rack['A1']
    mm_source.load_liquid(master_mix_def, volume=500)  # reasonable excess

    # Samples: each gets ~100 µL to cover the 2 µL × 3 replicates × 6 samples = 36 µL demand
    for pos, liq in sample_liq_map.items():
        sample_block[pos].load_liquid(liq, volume=100)

    # ---- Pipette -----------------------------------------------------------
    p20 = protocol.load_instrument('p20_single_gen2', 'left', tip_racks=[tiprack])

    # ---- Distribution ------------------------------------------------------
    # For each sample, dispense into three consecutive wells (rows A‑C) of the same column
    for idx, pos in enumerate(sample_positions):
        col = idx + 1                     # column number (1‑based)
        sample_source = sample_block[pos]  # where the cDNA lives
        targets = [plate[f'{row}{col}'] for row in ('A', 'B', 'C')]

        p20.pick_up_tip()
        for well in targets:
            # Add master mix (8 µL)
            p20.aspirate(8, mm_source)
            p20.dispense(8, well)
            # Add sample (2 µL)
            p20.aspirate(2, sample_source)
            p20.dispense(2, well)
        p20.drop_tip()

    # (Optional) home robot – not strictly required
    # protocol.home()
