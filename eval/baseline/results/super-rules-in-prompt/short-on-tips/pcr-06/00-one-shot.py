from opentrons import protocol_api

metadata = {
    "protocolName": "Colony PCR Prep",
    "author": "Automated Protocol Generator",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ----- Labware -----
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', '1')
    tuberack = protocol.load_labware('opentrons_24_tuberack_nest_1.5ml_snapcap', '2')
    colony_src = protocol.load_labware('nest_96_wellplate_200ul_flat', '3')
    pcr_dst = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', '4')

    # ----- Pipette -----
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])

    # ----- Liquids -----
    pcr_mix = protocol.define_liquid(
        name='pcr mix',
        description='PCR master mix for colony PCR',
        display_color='#FFA500'  # orange
    )

    # Prepare 16 colony liquids
    colony_colors = [
        '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
        '#8B0000', '#008B00', '#00008B', '#8B8B00', '#8B008B', '#008B8B',
        '#A52A2A', '#DEB887', '#5F9EA0', '#7FFF00'
    ]
    colony_liq = {}
    for i in range(1, 17):
        name = f'colony {i}'
        col = protocol.define_liquid(
            name=name,
            description=f'Resuspended colony {i}',
            display_color=color=(colony_colors[i-1])
        )
        colony_liq[name] = col

    # Load source liquids
    pcr_tube = tuberack['A1']
    pcr_tube.load_liquid(liquid=pcr_mix, volume=500)      # enough for 16×20 µL + excess

    # Colony source wells (A1‑A8, B1‑B8)
    src_wells = [f'{chr(ord("A")+r)}{c}' for r in range(2) for c in range(1, 9)]

    for idx, well_name in enumerate(src_wells, start=1):
        well = colony_src[well_name]
        well.load_liquid(liquid=colony_liq[f'colony {idx}'], volume=200)  # ample volume

    # Destination wells for the final reactions (same layout as sources)
    dst_wells = src_wells  # A1‑A8, B1‑B8 on the PCR plate

    # ----- Protocol (single tip) -----
    p20.pick_up_tip()
    for i, dst_well in enumerate(dst_wells):
        # 1️⃣ Dispense 20 µL PCR mix
        p20.aspirate(20, pcr_tube)
        p20.dispense(20, pcr_dst[dst_well])

        # 2️⃣ Add 1 µL from the corresponding colony suspension
        src_well = src_wells[i]
        p20.aspirate(1, colony_src[src_well])
        p20.dispense(1, pcr_dst[dst_well])

    p20.drop_tip()
