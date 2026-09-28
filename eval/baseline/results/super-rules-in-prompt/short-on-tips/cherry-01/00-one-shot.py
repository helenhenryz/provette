from opentrons import protocol_api

metadata = {
    "protocolName": "Cherrypick 10 µL selections",
    "author": "Assistant",
    "date": "2025-09-25",
    "description": "Transfer 10 µL from specified source wells to consecutive destination wells starting at A1.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # --- Labware ------------------------------------------------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_20ul', 1)          # for p20 single
    src_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 2)
    dst_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 3)

    # --- Pipette ------------------------------------------------------------
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tiprack])

    # --- Liquid definitions -------------------------------------------------
    sample = protocol.define_liquid(
        name='sample',
        description='Sample liquid to be transferred',
        display_color='#FF0000'
    )

    # Initialise source wells with enough volume for 10 µL pull-out each
    src_coords = ['B3', 'C7', 'D1', 'A12', 'H6', 'E5', 'F9', 'G2', 'B11', 'C4']
    for well_name in src_coords:
        src_plate[well_name].load_liquid(liquid=sample, volume=80)   # ≤100 µL well limit

    # Generate destination wells: A1, A2, ..., A10 (first 10 consecutive wells)
    dest_wells = []
    for i in range(10):
        col = (i % 12) + 1                     # column 1‑12
        row_idx = i // 12                       # 0‑based row index
        row_char = chr(ord('A') + row_idx)
        dest_wells.append(f'{row_char}{col}')
    
    # Perform transfers – one tip per transfer (minimum feasible to respect contamination rules)
    for src, dst in zip(src_coords, dest_wells):
        p20.pick_up_tip()
        p20.aspirate(10, src_plate[src].bottom(z=1))   # aspirate near bottom
        p20.dispense(10, dst_plate[dst].top(z=-1))     # dispense near top
        p20.blow_out(dst_plate[dst])
        p20.drop_tip()

if __name__ == '__main__':
    # This allows running the file directly for quick testing (optional)
    from opentrons import simulate
    simulate.get_protocol_api('2.19')(run)
