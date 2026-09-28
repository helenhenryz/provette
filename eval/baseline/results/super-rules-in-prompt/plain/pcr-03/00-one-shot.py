from opentrons import protocol_api

metadata = {
    "protocolName": "PCR Master Mix and Template Distribution",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- labware -----
    tiprack1 = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    tiprack2 = protocol.load_labware('opentrons_96_tiprack_20ul', '2')
    mix_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '3')
    sample_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '4')
    pcr_plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', '5')

    # ----- pipette -----
    p20 = protocol.load_instrument('p20_single_gen2', 'right',
                                   tip_racks=[tiprack1, tiprack2])

    # ----- liquids -----
    master_mix = protocol.define_liquid(
        name='master mix',
        description='PCR master mix',
        display_color='#00FF00'
    )

    # master mix in a 15 ml tube (tuberack)
    mix_tube = mix_rack['A1']
    mix_tube.load_liquid(liquid=master_mix, volume=2000)

    # define a unique liquid for each sample well
    rows = 'ABCDEFGHI'
    for r in rows:
        for c in range(1, 13):
            well_name = f'{r}{c}'
            liq_name = f'template_{well_name}'
            liq = protocol.define_liquid(
                name=liq_name,
                description=f'Template DNA for {well_name}',
                display_color='#FF0000'
            )
            sample_plate[well_name].load_liquid(liquid=liq, volume=20)

    # ----- liquid handling -----
    for col_num in range(1, 13):
        col = str(col_num)

        # ---- add template (2 µL) ----
        p20.pick_up_tip()
        p20.aspirate(2, sample_plate.columns()[col])
        p20.dispense(2, pcr_plate.columns()[col])
        p20.drop_tip()

        # ---- add master mix (18 µL) ----
        p20.pick_up_tip()
        p20.aspirate(18, mix_tube)
        p20.dispense(18, pcr_plate.columns()[col])
        # mix after master‑mix addition to avoid “well never mixed” warning
        p20.mix(repetitions=4, volume=10, pcr_plate.columns()[col])
        p20.drop_tip()
