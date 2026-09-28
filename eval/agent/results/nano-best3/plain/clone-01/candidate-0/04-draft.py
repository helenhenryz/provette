from opentrons import protocol_api

metadata = {
    'protocolName': 'restriction_digest_12',
    'apiLevel': '2.19'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module on slot 1
    temp_module = protocol.load_module('temperature module gen2', 1)
    # Set temperature to 4°C for the block
    temp_module.set_temperature(4)
    # Load aluminium block onto the temperature module
    source_block = temp_module.load_labware('opentrons_24_aluminumblock_nest_1.5ml_snapcap')
    # Load PCR plate on slot 2
    plate = protocol.load_labware('biorad_96_wellplate_200ul_pcr', 2)
    # Load tip rack on slot 3
    tips = protocol.load_labware('opentrons_96_filtertiprack_20ul', 3)
    # Load p20 single gen2 on the right mount, using the tip rack
    p20 = protocol.load_instrument('p20_single_gen2', 'right', tip_racks=[tips])

    # Define liquids
    buffer = protocol.define_liquid(name='buffer', description='10x restriction enzyme buffer', display_color='#0000FF')
    enzyme = protocol.define_liquid(name='enzyme', description='Restriction enzyme', display_color='#FF0000')
    water = protocol.define_liquid(name='water', description='Molecular biology grade water', display_color='#00FFFF')
    plasmid_1 = protocol.define_liquid(name='plasmid 1', description='Plasmid 1', display_color='#FFFFFF')
    plasmid_2 = protocol.define_liquid(name='plasmid 2', description='Plasmid 2', display_color='#FFFFFF')
    plasmid_3 = protocol.define_liquid(name='plasmid 3', description='Plasmid 3', display_color='#FFFFFF')
    plasmid_4 = protocol.define_liquid(name='plasmid 4', description='Plasmid 4', display_color='#FFFFFF')
    plasmid_5 = protocol.define_liquid(name='plasmid 5', description='Plasmid 5', display_color='#FFFFFF')
    plasmid_6 = protocol.define_liquid(name='plasmid 6', description='Plasmid 6', display_color='#FFFFFF')
    plasmid_7 = protocol.define_liquid(name='plasmid 7', description='Plasmid 7', display_color='#FFFFFF')
    plasmid_8 = protocol.define_liquid(name='plasmid 8', description='Plasmid 8', display_color='#FFFFFF')
    plasmid_9 = protocol.define_liquid(name='plasmid 9', description='Plasmid 9', display_color='#FFFFFF')
    plasmid_10 = protocol.define_liquid(name='plasmid 10', description='Plasmid 10', display_color='#FFFFFF')
    plasmid_11 = protocol.define_liquid(name='plasmid 11', description='Plasmid 11', display_color='#FFFFFF')
    plasmid_12 = protocol.define_liquid(name='plasmid 12', description='Plasmid 12', display_color='#FFFFFF')

    # Load liquids into source block wells
    source_block['A1'].load_liquid(liquid=buffer, volume=200)
    source_block['A2'].load_liquid(liquid=enzyme, volume=200)
    source_block['A3'].load_liquid(liquid=water, volume=500)
    source_block['A4'].load_liquid(liquid=plasmid_1, volume=100)
    source_block['A5'].load_liquid(liquid=plasmid_2, volume=100)
    source_block['A6'].load_liquid(liquid=plasmid_3, volume=100)
    source_block['B1'].load_liquid(liquid=plasmid_4, volume=100)
    source_block['B2'].load_liquid(liquid=plasmid_5, volume=100)
    source_block['B3'].load_liquid(liquid=plasmid_6, volume=100)
    source_block['B4'].load_liquid(liquid=plasmid_7, volume=100)
    source_block['B5'].load_liquid(liquid=plasmid_8, volume=100)
    source_block['B6'].load_liquid(liquid=plasmid_9, volume=100)
    source_block['C1'].load_liquid(liquid=plasmid_10, volume=100)
    source_block['C2'].load_liquid(liquid=plasmid_11, volume=100)
    source_block['C3'].load_liquid(liquid=plasmid_12, volume=100)

    # Get the first 12 wells of the plate
    dest_wells = plate.wells()[:12]

    # Perform the digests
    # Map each plasmid index to a source well label
    source_plasmid_wells = ['A4', 'A5', 'A6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'C1', 'C2', 'C3']
    for i, dest_well in enumerate(dest_wells):
        # Water (12 ul) - fresh tip
        p20.pick_up_tip()
        p20.aspirate(12, source_block['A3'])
        p20.dispense(12, dest_well)
        p20.drop_tip()
        # Buffer (2 ul) - fresh tip
        p20.pick_up_tip()
        p20.aspirate(2, source_block['A1'])
        p20.dispense(2, dest_well)
        p20.drop_tip()
        # Plasmid (5 ul) - fresh tip
        plasmid_well = source_block[source_plasmid_wells[i]]
        p20.pick_up_tip()
        p20.aspirate(5, plasmid_well)
        p20.dispense(5, dest_well)
        p20.drop_tip()
        # Enzyme (1 ul) - fresh tip
        p20.pick_up_tip()
        p20.aspirate(1, source_block['A2'])
        p20.dispense(1, dest_well)
        # Mix the well
        p20.mix(5, 10, dest_well)
        p20.drop_tip()
    
    # Deactivate temperature module at the end
    temp_module.deactivate()
