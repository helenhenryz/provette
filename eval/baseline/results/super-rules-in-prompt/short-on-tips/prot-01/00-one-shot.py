from opentrons import protocol_api

metadata = {
    "protocolName": "SDS-PAGE sample preparation with dye",
    "author": "",
    "description": "Mix 15 µL protein sample with 5 µL 4× loading dye for 12 samples.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    sample_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '2')  # protein samples
    tube_rack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '3')  # dye tube
    pcr_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '4')  # destination for mixes

    # ----- Liquids -----
    # Dye
    dye = protocol.define_liquid(
        name='dye',
        description='4× loading dye',
        display_color='#FFA500'  # orange
    )
    tube_rack['A1'].load_liquid(dye, volume=500)  # excess dye

    # Protein samples (sample 1 .. sample 12)
    for i in range(12):
        liq_name = f'sample {i+1}'
        liq_display = f'#{i*20:02X}{i*15:02X}{i*10:02X}'  # varied colours
        sample_liq = protocol.define_liquid(
            name=liq_name,
            description=f'protein sample {i+1}',
            display_color=liq_display
        )
        row = chr(ord('A') + (i // 8))
        col = (i % 8) + 1
        well = sample_plate[f'{row}{col}']
        well.load_liquid(sample_liq, volume=200)  # reasonable starting volume

    # ----- Pipette -----
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tips])

    # ----- Protocol -----
    for i in range(12):
        # Source (sample) well
        src_row = chr(ord('A') + (i // 8))
        src_col = (i % 8) + 1
        src = sample_plate[f'{src_row}{src_col}']

        # Destination well in PCR plate (same coordinates)
        dst_row = chr(ord('A') + (i // 8))
        dst_col = (i % 8) + 1
        dst = pcr_plate[f'{dst_row}{dst_col}']

        p20.pick_up_tip()
        # Take sample
        p20.aspirate(15, src)
        # Add dye
        p20.aspirate(5, tube_rack['A1'])
        # Dispense mixture
        p20.dispense(20, dst)
        # Clear tip
        p20.blow_out(dst)
        p20.touch_tip(dst)
        p20.drop_tip()
