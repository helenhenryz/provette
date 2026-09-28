from opentrons import protocol_api

metadata = {
    "protocolName": "Aliquot protein stock",
    "author": "",
    "description": "Transfer 50 µL of protein from a 15 mL tube into 48 PCR‑strip tubes.",
    "apiLevel": "2.19"
}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- Labware ----------
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    source_rack = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical',
                                       '2')
    # Aluminium block that holds 8‑tube PCR strips (96 positions)
    dest_block = protocol.load_labware('opentrons_96_aluminumblock_generic_pcr_strip_200ul',
                                      '3')

    # ---------- Liquids ----------
    protein = protocol.define_liquid(
        name='protein',
        description='Protein stock solution',
        display_color='#FF7F0E'
    )
    # Fill the source tube (use a realistic volume, e.g., 12 mL)
    src_well = source_rack['A1']
    src_well.load_liquid(liquid=protein, volume=12000)   # 12 µL? actually 12 mL

    # ---------- Pipette ----------
    p300 = protocol.load_instrument('p300_single_gen2',
                                    'right',
                                    tip_racks=[tiprack])

    # Prepare destination wells (first 48 positions of the block)
    dest_wells = dest_block.wells()[:48]   # leaves remaining wells unused

    # Perform the aliquoting using a fresh tip for each transfer
    for dst in dest_wells:
        p300.pick_up_tip()
        p300.aspirate(50, src_well)       # take 50 µL from protein stock
        p300.dispense(50, dst)            # deposit into a strip tube
        p300.drop_tip()                   # discard tip immediately
