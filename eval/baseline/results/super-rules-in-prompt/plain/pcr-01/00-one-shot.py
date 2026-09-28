from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Setup for 8 samples",
    "author": "Assistant",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    # Tips for P20 pipette (will be used for both master mix and sample transfers)
    tiprack_20 = protocol.load_rolarack('opentrons_96_tiprack_20ul', 1)
    # Tuberack for master mix and samples (1.5 ml snap‑cap tubes)
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', 2)
    # PCR plate for reactions
    plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)

    # ----- Pipette -----
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack_20])

    # ----- Liquids -----
    master_mix = protocol.define_liquid(
        name='master mix',
        description='PCR master mix',
        display_color='#FFA500'
    )
    sample_defs = []
    for i in range(8):
        sample = protocol.define_liquid(
            name=f'sample {i+1}',
            description=f'DNA sample #{i+1}',
            display_color=[
                '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
                '#FF00FF', '#00FFFF', '#800080', '#A52A2A'
            ][i]
        )
        sample_defs.append(sample)

    # ----- Load initial liquids -----
    # Wells in the tuberack ordered linearly (row‑major)
    all_tuberack_wells = tuberack.wells()
    master_mix_well = all_tuberack_wells[0]          # A1 – master mix
    sample_wells = all_tuberack_wells[1:9]           # A2‑A9 – the eight samples

    master_mix_well.load_liquid(master_mix, volume=1000)   # ~1 mL available
    for well, liq in zip(sample_wells, sample_defs):
        well.load_liquid(liq, volume=500)                 # ~500 µL each

    # ----- Transfer steps -----
    num_reactions = 8
    vol_mm = 20      # µL master mix per reaction
    vol_sm = 5       # µL sample per reaction

    for i in range(num_reactions):
        dest_well = plate.wells()[i]                # A1, A2, … A8 on the plate

        # ---- Master mix ---- transfer
        p20.pick_up_tip()
        p20.aspirate(vol_mm, master_mix_well)
        p20.dispense(vol_mm, dest_well)
        p20.drop_tip()

        # ---- Sample ---- transfer
        p20.pick_up_tip()
        p20.aspirate(vol_sm, sample_wells[i])
        p20.dispense(vol_sm, dest_well)
        p20.drop_tip()
